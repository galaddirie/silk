from typing import TypeVar, Generic, Callable, Any, Dict, List, Optional, Protocol, Awaitable, Union, overload, cast
from expression import pipe as expression_pipe, curry
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

import asyncio
from functools import reduce

from silk.browser.driver import BrowserDriver
from silk.actions.base import Action, create_action

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')


@curry
def sequence(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Combines multiple actions into a single action that executes them in sequence.
    
    Unlike 'compose', this function collects and returns ALL results as a Block.
    
    Example:
        result = await sequence(action1, action2, action3)(driver)
        # result is Ok(Block[result1, result2, result3])
    
    Args:
        *actions: Actions to combine
        
    Returns:
        A new Action that executes all actions in sequence and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a sequence with no actions")
    
    async def execute_sequence(driver: BrowserDriver) -> Result[Block[Any], Exception]:
        # Start with empty immutable Block
        results = Block.empty()
        
        for action in action_list:
            result = await action.execute(driver)
            
            # Use monadic bind to handle railway-oriented programming
            if result.is_error():
                return Error(result.error)
            
            # Cons is the immutable way to add an element to a Block (creates a new Block)
            results = results.cons(result.value)
        
        # Block's elements are added in reverse order when using cons, so we need to reverse
        return Ok(expression_pipe(results, Block.reverse))
    
    action_names = " >> ".join(a.name for a in action_list)
    return create_action(
        name=f"sequence({action_names})",
        execute_fn=execute_sequence,
        description=f"Sequence of actions (all results): {action_names}"
    )


@curry
def parallel(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Execute multiple actions in parallel and collect their results into a Block.
    
    If any action fails, the whole operation fails with that error.
    
    Example:
        result = await parallel(action1, action2, action3)(driver)
        # result is Ok(Block[result1, result2, result3])
    
    Args:
        *actions: Actions to execute in parallel
        
    Returns:
        A new Action that executes all actions in parallel and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a parallel execution with no actions")
    
    async def execute_parallel(driver: BrowserDriver) -> Result[Block[Any], Exception]:
        tasks = [action.execute(driver) for action in action_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results using functional patterns
        # Find first error if any
        error_result = expression_pipe(
            results,
            Block.of_seq,
            Block.try_find(lambda r: isinstance(r, Exception) or 
                          (isinstance(r, Result) and r.is_error()))
        )
        
        if error_result is not Nothing:
            error = error_result.value
            if isinstance(error, Exception):
                return Error(error)
            return Error(error.error())
        
        # Map successful results to values
        values = expression_pipe(
            results,
            Block.of_seq,
            Block.map(lambda r: r.value if isinstance(r, Result) else r)
        )
        
        return Ok(values)
    
    action_names = " & ".join(a.name for a in action_list)
    return create_action(
        name=f"parallel({action_names})",
        execute_fn=execute_parallel,
        description=f"Parallel actions: {action_names}"
    )


@curry
def pipe(*actions: Action[Any]) -> Action[Any]:
    """
    Create a pipeline of actions where each action receives the result of the previous action.
    
    This differs from 'compose' in that each action in the chain can use the result
    of the previous action, instead of just executing in sequence.
    
    Example:
        result = await pipe(
            extract_text(selector),      # Returns "42"
            lambda val: multiply(val, 2) # Uses "42" as input, returns 84
        )(driver)
        # result is Ok(84)
    
    Args:
        *actions: Actions to pipe together
        
    Returns:
        A new Action that executes the actions in a pipeline
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a pipeline with no actions")
    if len(action_list) == 1:
        return action_list[0]
    
    async def execute_pipeline(driver: BrowserDriver) -> Result[Any, Exception]:
        try:
            # Start with first action
            result = await action_list[0].execute(driver)
            if result.is_error():
                return result
            
            value = result.value
            
            # Chain remaining actions using railway pattern
            for action in action_list[1:]:
                # Handle both Actions and callables that return Actions
                next_action = action(value) if callable(action) and not isinstance(action, Action) else action
                result = await next_action.execute(driver)
                if result.is_error():
                    return result
                value = result.value
            
            return Ok(value)
        except Exception as e:
            return Error(e)
    
    action_names = " |> ".join(a.name for a in action_list)
    return create_action(
        name=f"pipe({action_names})",
        execute_fn=execute_pipeline,
        description=f"Pipeline of actions (values flow through): {action_names}"
    )


@curry
def fallback(*actions: Action[T]) -> Action[T]:
    """
    Try actions in sequence until one succeeds.
    
    This is equivalent to the '|' operator between Actions.
    
    Example:
        result = await fallback(
            action_might_fail, 
            backup_action
        )(driver)
        # Returns result of first action that succeeds
    
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
    
    async def execute_fallback(driver: BrowserDriver) -> Result[T, Exception]:
        # Use fold to accumulate the result or the last error
        # Initial state is a Error with a default message
        initial_error = Error(Exception("No actions to try"))
        
        # Sequentially try each action, returning the first success or last error
        result = initial_error
        for action in action_list:
            try:
                result = await action.execute(driver)
                if result.is_ok():
                    return result
            except Exception as e:
                result = Error(e)
        
        return result
    
    action_names = " | ".join(a.name for a in action_list)
    return create_action(
        name=f"fallback({action_names})",
        execute_fn=execute_fallback,
        description=f"Fallback actions (try until success): {action_names}"
    )


def compose(*actions: Action[Any]) -> Action[Any]:
    """
    Compose multiple actions into a single action that executes them in sequence.
    
    Unlike 'sequence', this function only returns the LAST result.
    This is equivalent to chaining actions with the '>>' operator.
    
    Example:
        result = await compose(action1, action2, action3)(driver)
        # result is Ok(result3) - only the last action's result
    
    Args:
        *actions: Actions to compose into a single action
        
    Returns:
        A single Action that executes actions in sequence and returns the last result
    """
    # Handle edge cases
    if not actions:
        raise ValueError("Cannot compose zero actions")
    if len(action_list := list(actions)) == 1:
        return action_list[0]
    
    # Use reduce to combine actions with the >> operator
    return reduce(lambda acc, action: acc >> action, action_list) 