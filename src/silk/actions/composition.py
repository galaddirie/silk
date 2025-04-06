from typing import TypeVar, Generic, Callable, Any, Dict, List, Optional, Protocol, Awaitable, Union, overload, cast, Literal
from expression import pipe as expression_pipe, curry
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

import asyncio
from functools import reduce

from silk.browsers.driver import BrowserDriver
from silk.models.browser import ActionContext
from silk.actions.base import Action, create_action

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')


def sequence(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Combines multiple actions into a single action that executes them in sequence.
    
    Unlike 'compose', this function collects and returns ALL results as a Block.
    
    Example:
    ```python
        result = await sequence(action1, action2, action3)(driver)
        # result is Ok(Block[result1, result2, result3])
    ```
    
    Args:
        *actions: Actions to combine
        
    Returns:
        A new Action that executes all actions in sequence and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a sequence with no actions")
    
    class SequenceAction(Action[Block[Any]]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Block[Any], Exception]:
            # Use provided context or create a new one
            ctx = context or ActionContext()
            
            # Start with empty immutable Block
            results = Block.empty()
            
            for action in action_list:
                try:
                    result = await action.execute(driver, ctx)
                    
                    # Use monadic bind to handle railway-oriented programming
                    if result.is_error():
                        return Error(result.error)
                    
                    value = result.value if hasattr(result, 'value') else None
                    results = results.cons(value)
                except Exception as e:
                    return Error(e)
            
            return Ok(results.sort(reverse=True))
    
    return SequenceAction()


def parallel(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Execute multiple actions in parallel and collect their results into a Block.
    
    If any action fails, the whole operation fails with that error.
    
    Example:
    ```python
        result = await parallel(action1, action2, action3)(driver)
        # result is Ok(Block[result1, result2, result3])
    ```
    
    Args:
        *actions: Actions to execute in parallel
        
    Returns:
        A new Action that executes all actions in parallel and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a parallel execution with no actions")
    
    class ParallelAction(Action[Block[Any]]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Block[Any], Exception]:
            # Use provided context or create a new one
            ctx = context or ActionContext()
            
            # Create a task for each action with the same context
            tasks = [action.execute(driver, ctx) for action in action_list]
            
            try:
                # Gather results in parallel
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results using functional patterns
                # Create a Block from results
                results_block = Block.of_seq(results)
                
                # Find first error if any
                for result in results_block:
                    if isinstance(result, Exception):
                        return Error(result)
                    if isinstance(result, Result) and hasattr(result, 'error') and result.is_error():
                        return Error(result.error)
                
                # Map successful results to values
                values = Block.empty()
                for result in results_block:
                    if isinstance(result, Result):
                        value = result.value if hasattr(result, 'value') else None
                        values = values.cons(value)
                    else:
                        values = values.cons(result)
                
                # Reverse to maintain original order
                return Ok(values.sort(reverse=True))
            except Exception as e:
                return Error(e)
    
    return ParallelAction()


def pipe(*actions: Union[Action[Any], Callable[[Any], Action[Any]]]) -> Action[Any]:
    """
    Create a pipeline of actions where each action receives the result of the previous action.
    
    This differs from 'compose' in that each action in the chain can use the result
    of the previous action, instead of just executing in sequence.
    
    Example:
    ```python
        result = await pipe(
            extract_text(selector),      # Returns "42"
            lambda val: multiply(val, 2) # Uses "42" as input, returns 84
        )(driver)
        # result is Ok(84)
    ```
    
    Args:
        *actions: Actions to pipe together. Can be Action objects or callables that take a value and return an Action.
        
    Returns:
        A new Action that executes the actions in a pipeline
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a pipeline with no actions")
    if len(action_list) == 1:
        # If we only have one action, just return it (no need to create a wrapper)
        first_action = action_list[0]
        if callable(first_action) and not isinstance(first_action, Action):
            raise ValueError("First item in pipe must be an Action, not a callable")
        return first_action
    
    class PipelineAction(Action[Any]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
            # Use provided context or create a new one
            ctx = context or ActionContext()
            
            try:
                # Start with first action (must be an Action, not a callable)
                first_action = action_list[0]
                if callable(first_action) and not isinstance(first_action, Action):
                    return Error(Exception("First item in pipe must be an Action, not a callable"))
                
                result = await first_action.execute(driver, ctx)
                if result.is_error():
                    return result
                
                value = result.value if hasattr(result, 'value') else None
                
                # Chain remaining actions using railway pattern
                for action in action_list[1:]:
                    try:
                        # Handle both Actions and callables that return Actions
                        next_action = action(value) if callable(action) and not isinstance(action, Action) else action
                        
                        if not isinstance(next_action, Action):
                            return Error(Exception(f"Expected an Action but got {type(next_action)}: {next_action}"))
                        
                        result = await next_action.execute(driver, ctx)
                        if result.is_error():
                            return result
                        
                        value = result.value if hasattr(result, 'value') else None
                    except Exception as e:
                        return Error(e)
                
                return Ok(value)
            except Exception as e:
                return Error(e)
    
    return PipelineAction()


def fallback(*actions: Action[T]) -> Action[T]:
    """
    Try actions in sequence until one succeeds.
    
    This is equivalent to the '|' operator between Actions.
    
    Example:
    ```python
        result = await fallback(
            action_might_fail, 
            backup_action
        )(driver)
        # Returns result of first action that succeeds
    ```
    
    Args:
        *actions: Actions to try in order
        
    Returns:
        A new Action that tries each action until one succeeds
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a fallback with no actions")
    if len(action_list) == 1:
        return action_list[0]
    
    class FallbackAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            # Use provided context or create a new one
            ctx = context or ActionContext()
            
            # Use a new context for each attempt that tracks which fallback we're on
            last_error = None
            
            # Sequentially try each action, returning the first success or last error
            for index, action in enumerate(action_list):
                try:
                    # Create a child context for each fallback attempt
                    fallback_context = ActionContext(
                        retry_count=0,
                        max_retries=ctx.max_retries,
                        retry_delay_ms=ctx.retry_delay_ms,
                        timeout_ms=ctx.timeout_ms,
                        parent_context=ctx,
                        metadata={
                            **ctx.metadata,
                            "fallback_index": index,
                            "fallback_total": len(action_list)
                        }
                    )
                    
                    result = await action.execute(driver, fallback_context)
                    if result.is_ok():
                        return result
                    
                    # Store the error for potential reporting
                    last_error = result.error if hasattr(result, 'error') else None
                except Exception as e:
                    last_error = e
            
            # If we got here, all actions failed
            return Error(last_error or Exception("All fallback actions failed"))
    
    return FallbackAction()


def compose(*actions: Action[Any]) -> Action[Any]:
    """
    Compose multiple actions into a single action that executes them in sequence.
    
    Unlike 'sequence', this function only returns the LAST result.
    This is equivalent to chaining actions with the '>>' operator.
    
    Example:
    ```python
        result = await compose(action1, action2, action3)(driver)
        # result is Ok(result3) - only the last action's result
    ```
    
    Args:
        *actions: Actions to compose into a single action
        
    Returns:
        A single Action that executes actions in sequence and returns the last result
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot compose zero actions")
    if len(action_list) == 1:
        return action_list[0]
    
    class ComposeAction(Action[Any]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
            ctx = context or ActionContext()
            
            try:
                # Execute each action in sequence, returning the last result
                result = None
                
                for action in action_list:
                    result = await action.execute(driver, ctx)
                    if result.is_error():
                        return result
                
                return result
            except Exception as e:
                return Error(e)
    
    return ComposeAction()


def retry(action: Action[T], max_attempts: int = 3, delay_ms: int = 1000) -> Action[T]:
    """
    Create a new action that retries the original action until it succeeds.
    
    This is a convenience function that wraps the Action.retry() method.
    
    Example:
    ```python
        result = await retry(
            action_that_might_fail,
            max_attempts=3,
            delay_ms=500
        )(driver)
    ```
    
    Args:
        action: Action to retry
        max_attempts: Maximum number of attempts
        delay_ms: Delay between attempts in milliseconds
        
    Returns:
        A new Action with retry logic
    """
    return action.retry(max_attempts, delay_ms)


def with_timeout(action: Action[T], timeout_ms: int) -> Action[T]:
    """
    Create a new action that times out after the specified duration.
    
    This is a convenience function that wraps the Action.with_timeout() method.
    
    Example:
    ```python
        result = await with_timeout(
            action_that_might_hang,
            timeout_ms=5000
        )(driver)
    ```
    
    Args:
        action: Action to execute with timeout
        timeout_ms: Timeout in milliseconds
        
    Returns:
        A new Action with timeout logic
    """
    return action.with_timeout(timeout_ms)