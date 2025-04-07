from typing import TypeVar, Generic, Callable, Any, Dict, List, Optional, Protocol, Awaitable, Union, overload, cast, Literal
from expression import pipe as expression_pipe, curry
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

import asyncio
from functools import reduce

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
        result = await sequence(action1, action2, action3).execute(context)
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
        async def execute(self, context: ActionContext) -> Result[Block[Any], Exception]:
            # Start with empty immutable Block
            results = Block.empty()
            
            for action in action_list:
                try:
                    result = await action.execute(context)
                    
                    # Use monadic bind to handle railway-oriented programming
                    if result.is_error():
                        return Error(result.error)
                    
                    value = result.default_value(None)
                    if value is not None:
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
        result = await parallel(action1, action2, action3).execute(context)
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
        async def execute(self, context: ActionContext) -> Result[Block[Any], Exception]:
            if not context.browser_manager:
                return Error(Exception("Cannot execute parallel actions without a browser manager"))
                
            try:
                # Create tasks for executing each action with its own separate context
                tasks = []
                context_ids = []
                
                for action in action_list:
                    # Create a new context for each action
                    context_result = await context.browser_manager.create_context()
                    if context_result.is_error():
                        return Error(Exception(f"Failed to create context for parallel execution: {context_result.error}"))
                        
                    browser_context = context_result.default_value(None)
                    if browser_context is None:
                        return Error(Exception("Failed to create browser context for parallel execution"))
                    
                    context_ids.append(browser_context.id)
                    
                    # Get default page
                    page_result = browser_context.get_page()
                    if page_result.is_error():
                        return Error(Exception(f"Failed to get page for parallel execution: {page_result.error}"))
                        
                    page = page_result.default_value(None)
                    if page is None:
                        return Error(Exception("Failed to get page for parallel execution"))
                    
                    # Create action context
                    action_context = ActionContext(
                        browser_manager=context.browser_manager,
                        context_id=browser_context.id,
                        page_id=page.id,
                        metadata={**context.metadata, "parallel_execution": True}
                    )
                    
                    # Create task
                    task = action.execute(action_context)
                    tasks.append(task)
                
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
                        if isinstance(result, Result) and result.is_error():
                            return Error(result.error)
                    
                    # Map successful results to values
                    values = Block.empty()
                    for result in results_block:
                        if isinstance(result, Result):
                            value = result.default_value(None)
                            if value is not None:
                                values = values.cons(value)
                        else:
                            values = values.cons(result)
                    
                    # Reverse to maintain original order
                    return Ok(values.sort(reverse=True))
                finally:
                    # Clean up the contexts
                    for context_id in context_ids:
                        await context.browser_manager.close_context(context_id)
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
        ).execute(context)
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
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                # Start with first action (must be an Action, not a callable)
                first_action = action_list[0]
                if callable(first_action) and not isinstance(first_action, Action):
                    return Error(Exception("First item in pipe must be an Action, not a callable"))
                
                result = await first_action.execute(context)
                if result.is_error():
                    return result
                
                value = result.default_value(None)
                if value is None:
                    return Error(Exception("First action in pipe returned None"))
                
                # Chain remaining actions using railway pattern
                for action in action_list[1:]:
                    try:
                        # Handle both Actions and callables that return Actions
                        next_action = action(value) if callable(action) and not isinstance(action, Action) else action
                        
                        if not isinstance(next_action, Action):
                            return Error(Exception(f"Expected an Action but got {type(next_action)}: {next_action}"))
                        
                        result = await next_action.execute(context)
                        if result.is_error():
                            return result
                        
                        value = result.default_value(None)
                        if value is None:
                            return Error(Exception("Action in pipe returned None"))
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
        ).execute(context)
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
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            # Sequentially try each action, returning the first success or last error
            last_error = None
            
            for index, action in enumerate(action_list):
                try:
                    # Create a child context for each fallback attempt
                    fallback_context = context.derive(
                        metadata={
                            "fallback_index": index,
                            "fallback_total": len(action_list)
                        }
                    )
                    
                    result = await action.execute(fallback_context)
                    if result.is_ok():
                        return result
                    
                    # Store the error for potential reporting
                    last_error = result.error
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
        result = await compose(action1, action2, action3).execute(context)
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
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                # Execute the first action to initialize the result
                result = await action_list[0].execute(context)
                if result.is_error():
                    return result
                
                # Execute remaining actions in sequence
                for action in action_list[1:]:
                    result = await action.execute(context)
                    if result.is_error():
                        return result
                
                return result
            except Exception as e:
                return Error(e)
    
    return ComposeAction()