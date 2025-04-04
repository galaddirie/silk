from typing import TypeVar, Generic, Callable, Any, Dict, List, Optional, Union, cast, overload
import asyncio
import random
from dataclasses import dataclass
from functools import wraps
import logging

from expression import pipe, curry, effect
from expression.core import Result, Ok, Error, Option, Some, Nothing
from expression.collections import Block

from silk.browser.driver import BrowserDriver
from silk.actions.base import Action, create_action

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')

logger = logging.getLogger(__name__)


@curry
def branch(input_value: T, 
           predicate: Callable[[T], bool], 
           true_action: Action[S], 
           false_action: Optional[Action[S]] = None) -> Action[Union[S, T]]:
    """
    Branch based on a predicate, using the input_value from a previous action.
    
    Args:
        input_value: The value to test with the predicate
        predicate: Function that takes the input_value and returns True/False
        true_action: Action to execute if predicate returns True
        false_action: Optional action to execute if predicate returns False
                      If not provided, the original value is returned unchanged
    
    Returns:
        An Action that branches based on the predicate result

    Example:
    ```
        # Branch based on whether a login button is visible
        login_flow = get_element("#login-button") >> branch(
            predicate=lambda element: element.is_visible(),
            true_action=click(),
            false_action=navigate_to("/dashboard")
        )
        
        # Branch based on a text value
        message_handler = get_text(".message") >> branch(
            predicate=lambda text: "error" in text.lower(),
            true_action=log_error() >> retry_action(),
            false_action=continue_processing()
        )
    ```
    """
    async def execute_branch(driver: BrowserDriver) -> Result[Union[S, T], Exception]:
        try:
            # Check predicate with the provided input value
            if predicate(input_value):
                return await true_action.execute(driver)
            elif false_action is not None:
                return await false_action.execute(driver)
            else:
                # Pass through the original value
                return Ok(input_value)
        except Exception as e:
            return Error(e)
    
    action_name = f"branch({true_action.name}" + (f", {false_action.name})" if false_action else ")")
    
    return create_action(
        name=action_name,
        execute_fn=execute_branch,
        description="Branch to different actions based on a predicate"
    )


@curry
def loop_until(action: Action[T],
               condition: Callable[[T], bool],
               max_iterations: int = 10,
               delay_ms: int = 1000) -> Action[T]:
    """
    Repeatedly execute action until condition is met or max_iterations is reached.
    
    Args:
        action: The action to repeat
        condition: Function that takes the action result and returns True when done
        max_iterations: Maximum number of times to execute the action
        delay_ms: Delay between iterations in milliseconds
    
    Returns:
        An Action that loops until the condition is met

    Example:
    ```
        # Loop until a sale is found
        sale_finder = get_element("#sale") >> loop_until(
            condition=lambda element: element.is_visible(),
            action=click()
        )
    ``` 
    """
    async def execute_loop(driver: BrowserDriver) -> Result[T, Exception]:
        try:
            iterations = 0
            last_result = None
            
            while iterations < max_iterations:
                action_result = await action.execute(driver)
                
                if action_result.is_error():
                    return action_result
                    
                result_value = action_result.value
                last_result = result_value
                
                if condition(result_value):
                    return Ok(result_value)
                    
                iterations += 1
                if iterations < max_iterations:
                    logger.debug(f"Loop condition not met, iteration {iterations}/{max_iterations}")
                    await asyncio.sleep(delay_ms / 1000)
                else:
                    logger.debug(f"Reached max iterations ({max_iterations})")
            
            return Ok(last_result)
        except Exception as e:
            return Error(e)
    
    return create_action(
        name=f"loop_until({action.name}, max={max_iterations})",
        execute_fn=execute_loop,
        description=f"Loop action until condition is met (max {max_iterations} times)"
    )

# ------------ Enhanced Retry ------------

@curry
def retry_with_backoff(action: Action[T], 
                       max_attempts: int = 3,
                       initial_delay_ms: int = 1000,
                       backoff_factor: float = 2.0,
                       jitter: bool = True,
                       should_retry: Optional[Callable[[Exception], bool]] = None) -> Action[T]:
    """
    Retry action with exponential backoff and optional jitter.
    
    Args:
        action: The action to retry
        max_attempts: Maximum number of retry attempts
        initial_delay_ms: Initial delay between retries in milliseconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Add randomness to delay to prevent thundering herd
        should_retry: Optional function to determine if specific errors should trigger retry
    
    Returns:
        An Action with retry logic
    """
    async def execute_retry(driver: BrowserDriver) -> Result[T, Exception]:
        try:
            last_error = None
            delay = initial_delay_ms
            
            for attempt in range(max_attempts):
                try:
                    result = await action.execute(driver)
                    if result.is_ok():
                        return Ok(result.value)
                    
                    last_error = result.error()
                    # Check if we should retry this specific error
                    if should_retry and not should_retry(last_error):
                        return Error(last_error)
                        
                except Exception as e:
                    last_error = e
                    # Check if we should retry this specific error
                    if should_retry and not should_retry(e):
                        return Error(e)
                
                # If not the last attempt, wait before retrying
                if attempt < max_attempts - 1:
                    # Calculate backoff with optional jitter
                    current_delay = delay
                    if jitter:
                        # Add random jitter between 0.8x and 1.2x
                        jitter_factor = random.uniform(0.8, 1.2)
                        current_delay = current_delay * jitter_factor
                    
                    logger.info(f"Retry {attempt+1}/{max_attempts} failed, waiting {current_delay:.0f}ms")
                    await asyncio.sleep(current_delay / 1000)
                    
                    # Increase delay for next attempt
                    delay = delay * backoff_factor
            
            # All retries failed
            return Error(last_error or Exception(f"All {max_attempts} retry attempts failed"))
        except Exception as e:
            return Error(e)
    
    return create_action(
        name=f"retry_with_backoff({action.name}, {max_attempts}, {initial_delay_ms}ms)",
        execute_fn=execute_retry,
        description=f"Retry {action.name} with exponential backoff"
    )

# ------------ Timeout ------------

@curry
def with_timeout(action: Action[T], 
                 timeout_ms: int,
                 on_timeout: Optional[Callable[[], T]] = None) -> Action[T]:
    """
    Execute action with timeout. If timeout occurs, either raise
    TimeoutError or return result from on_timeout callback.
    
    Args:
        action: The action to execute with timeout
        timeout_ms: Timeout in milliseconds
        on_timeout: Optional callback to provide a default value on timeout
    
    Returns:
        An Action with timeout constraint

    Example:
    ```
        # Execute an action with a timeout
        result = await get_element("#login-button") >> with_timeout(
            timeout_ms=5000,
            on_timeout=lambda: print("Timeout occurred, returning default value")
        )   
    ``` 
    """
    async def execute_with_timeout(driver: BrowserDriver) -> Result[T, Exception]:
        try:
            # Run the action with a timeout
            try:
                result = await asyncio.wait_for(
                    action.execute(driver),
                    timeout=timeout_ms / 1000  # Convert to seconds
                )
                return result
            except asyncio.TimeoutError:
                if on_timeout:
                    # Return default value from callback
                    try:
                        return Ok(on_timeout())
                    except Exception as e:
                        return Error(e)
                else:
                    # Propagate timeout error
                    return Error(TimeoutError(f"Action timed out after {timeout_ms}ms"))
        except Exception as e:
            return Error(e)
    
    return create_action(
        name=f"with_timeout({action.name}, {timeout_ms}ms)",
        execute_fn=execute_with_timeout,
        description=f"Execute {action.name} with {timeout_ms}ms timeout"
    )

# ------------ Tap (Side Effects) ------------

@curry
def tap(side_effect_action: Action[Any]) -> Callable[[T], Action[T]]:
    """
    Execute an action for side effects without changing the pipeline value.
    
    Args:
        side_effect_action: Action to execute for side effects
    
    Returns:
        A function that takes an input value and returns an Action that preserves that value

    Example:
    ```
        # Execute an action for side effects
        result = await get_element("#login-button") >> tap(log_action())
    ``` 
    """
    def tap_with_value(input_value: T) -> Action[T]:
        async def execute_tap(driver: BrowserDriver) -> Result[T, Exception]:
            try:
                # Execute the side effect action
                side_effect_result = await side_effect_action.execute(driver)
                
                # Ignore the side effect result, just check for errors
                if side_effect_result.is_error():
                    return Error(side_effect_result.error())
                    
                # Return the original input value
                return Ok(input_value)
            except Exception as e:
                return Error(e)
        
        return create_action(
            name=f"tap({side_effect_action.name})",
            execute_fn=execute_tap,
            description=f"Execute {side_effect_action.name} as side effect"
        )
    
    return tap_with_value
