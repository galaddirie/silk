from typing import TypeVar, Generic, Callable, Any, Dict, List, Optional, Union, cast, overload
import asyncio
import random
import logging
from datetime import datetime

from expression import pipe, curry, effect
from expression.core import Result, Ok, Error, Option, Some, Nothing
from expression.collections import Block

from silk.browsers.driver import BrowserDriver
from silk.models.browser import ActionContext
from silk.actions.base import Action, create_action

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')

logger = logging.getLogger(__name__)


def branch(condition: Action[bool], 
           if_true: Action[S], 
           if_false: Optional[Action[S]] = None) -> Action[S]:
    """
    Branch execution based on the result of a condition action.
    
    Args:
        condition: An action that determines which branch to take (must return bool)
        if_true: Action to execute if condition is True
        if_false: Optional action to execute if condition is False
                  If not provided, returns None when condition is False
    
    Returns:
        An Action that branches based on the condition result

    Example:
    ```
        # Branch based on whether a login button is visible
        login_flow = branch(
            condition=is_visible("#login-button"),
            if_true=Click("#login-button"),
            if_false=Navigate("/dashboard")
        )
    ```
    """
    
    class BranchAction(Action[S]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
            ctx = context or ActionContext()
            
            try:
                # Create branch-specific context with metadata
                branch_ctx = ActionContext(
                    retry_count=ctx.retry_count,
                    max_retries=ctx.max_retries,
                    retry_delay_ms=ctx.retry_delay_ms,
                    timeout_ms=ctx.timeout_ms,
                    parent_context=ctx,
                    metadata={
                        **ctx.metadata,
                        "branch_operation": "condition",
                        "branch_timestamp": datetime.now().isoformat()
                    }
                )
                
                # Execute the condition action
                condition_result = await condition.execute(driver, branch_ctx)
                
                if condition_result.is_error():
                    return Error(Exception(f"Branch condition failed: {condition_result.error}"))
                
                # Get the boolean value from the condition result
                condition_value = condition_result.value if hasattr(condition_result, 'value') else False
                
                # Create context for the selected branch
                branch_path_ctx = ActionContext(
                    retry_count=ctx.retry_count,
                    max_retries=ctx.max_retries,
                    retry_delay_ms=ctx.retry_delay_ms,
                    timeout_ms=ctx.timeout_ms,
                    parent_context=ctx,
                    metadata={
                        **ctx.metadata,
                        "branch_path": "true" if condition_value else "false",
                        "branch_timestamp": datetime.now().isoformat()
                    }
                )
                
                if condition_value:
                    logger.debug("Branch condition is True, taking if_true path")
                    return await if_true.execute(driver, branch_path_ctx)
                elif if_false is not None:
                    logger.debug("Branch condition is False, taking if_false path")
                    return await if_false.execute(driver, branch_path_ctx)
                else:
                    # Return None when condition is False and no if_false is provided
                    logger.debug("Branch condition is False, no if_false path provided")
                    return Ok(cast(S, None))
            except Exception as e:
                return Error(e)
    
    return BranchAction()


def loop_until(condition: Action[bool],
               body: Action[T],
               max_iterations: int = 10,
               delay_ms: int = 1000) -> Action[T]:
    """
    Repeatedly execute body action until condition succeeds or max_iterations is reached.
    
    Args:
        condition: Action that determines when to stop looping (must return bool)
        body: Action to execute in each iteration
        max_iterations: Maximum number of times to execute the action
        delay_ms: Delay between iterations in milliseconds
    
    Returns:
        An Action that loops until the condition is met

    Example:
    ```
        # Loop until an element is visible
        sale_finder = loop_until(
            condition=is_visible("#sale-alert"),
            body=Click("#check-sales")
        )
    ``` 
    """
    
    class LoopUntilAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            ctx = context or ActionContext()
            
            try:
                iterations = 0
                last_result = None
                
                while iterations < max_iterations:
                    # Create iteration-specific context
                    iter_ctx = ActionContext(
                        retry_count=ctx.retry_count,
                        max_retries=ctx.max_retries,
                        retry_delay_ms=ctx.retry_delay_ms,
                        timeout_ms=ctx.timeout_ms,
                        parent_context=ctx,
                        metadata={
                            **ctx.metadata,
                            "loop_iteration": iterations + 1,
                            "loop_max_iterations": max_iterations,
                            "loop_timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    # First execute the body action
                    body_result = await body.execute(driver, iter_ctx)
                    
                    if body_result.is_error():
                        return body_result
                        
                    # Store the result value
                    last_result = body_result.value if hasattr(body_result, 'value') else None
                    
                    # Then check the condition
                    condition_result = await condition.execute(driver, iter_ctx)
                    
                    # If condition fails, we get an error or False
                    if condition_result.is_error():
                        iterations += 1
                        if iterations < max_iterations:
                            logger.debug(f"Loop condition check failed, iteration {iterations}/{max_iterations}")
                            await asyncio.sleep(delay_ms / 1000)
                        continue
                    
                    # Check actual boolean value
                    condition_value = condition_result.value if hasattr(condition_result, 'value') else False
                    
                    # If condition is True, return the body result
                    if condition_value:
                        logger.debug(f"Loop condition met at iteration {iterations + 1}")
                        return Ok(last_result)
                        
                    iterations += 1
                    if iterations < max_iterations:
                        logger.debug(f"Loop condition not met, iteration {iterations}/{max_iterations}")
                        await asyncio.sleep(delay_ms / 1000)
                    else:
                        logger.debug(f"Reached max iterations ({max_iterations})")
                
                # Return error if max iterations reached
                return Error(Exception(f"Maximum iterations ({max_iterations}) reached in loop_until"))
            except Exception as e:
                return Error(e)
    
    return LoopUntilAction()


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

    Example:
    ```
        # Retry with backoff, only for network errors
        robust_action = retry_with_backoff(
            action=FetchData(), 
            max_attempts=5,
            should_retry=lambda e: isinstance(e, NetworkError)
        )
    ```
    """
    
    class RetryWithBackoffAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            ctx = context or ActionContext()
            
            try:
                last_error = None
                delay: float = float(initial_delay_ms)
                
                for attempt in range(max_attempts):
                    # Create attempt-specific context
                    retry_ctx = ActionContext(
                        retry_count=attempt,
                        max_retries=max_attempts,
                        retry_delay_ms=int(delay),
                        timeout_ms=ctx.timeout_ms,
                        parent_context=ctx,
                        metadata={
                            **ctx.metadata,
                            "backoff_attempt": attempt + 1,
                            "backoff_max_attempts": max_attempts,
                            "backoff_delay_ms": delay,
                            "backoff_timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    try:
                        result = await action.execute(driver, retry_ctx)
                        if result.is_ok():
                            return result
                        
                        # Handle the error case
                        if hasattr(result, 'error'):
                            last_error = result.error
                            
                            # Check if we should retry this specific error
                            if should_retry and not should_retry(last_error):
                                logger.debug(f"Error not eligible for retry: {last_error}")
                                return result
                                
                    except Exception as e:
                        last_error = e
                        # Check if we should retry this specific error
                        if should_retry and not should_retry(e):
                            logger.debug(f"Exception not eligible for retry: {e}")
                            return Error(e)
                    
                    # If not the last attempt, wait before retrying
                    if attempt < max_attempts - 1:
                        # Calculate backoff with optional jitter
                        current_delay: float = delay
                        if jitter:
                            # Add random jitter between 0.8x and 1.2x
                            jitter_factor = random.uniform(0.8, 1.2)
                            current_delay = delay * jitter_factor
                        
                        logger.info(f"Retry {attempt+1}/{max_attempts} failed, waiting {current_delay:.0f}ms")
                        await asyncio.sleep(current_delay / 1000)
                        
                        # Increase delay for next attempt
                        delay = delay * backoff_factor
                
                # All retries failed
                return Error(last_error or Exception(f"Action failed after {max_attempts} retry attempts"))
            except Exception as e:
                return Error(e)
    
    return RetryWithBackoffAction()


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
        result = await with_timeout(
            action=GetElement("#login-button"),
            timeout_ms=5000,
            on_timeout=lambda: print("Timeout occurred") or None
        )(driver)   
    ``` 
    """
    
    class TimeoutAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            ctx = context or ActionContext()
            
            # Create timeout-specific context
            timeout_ctx = ActionContext(
                retry_count=ctx.retry_count,
                max_retries=ctx.max_retries,
                retry_delay_ms=ctx.retry_delay_ms,
                timeout_ms=timeout_ms,  # Override with specific timeout
                parent_context=ctx,
                metadata={
                    **ctx.metadata,
                    "timeout_ms": timeout_ms,
                    "timeout_timestamp": datetime.now().isoformat()
                }
            )
            
            try:
                # Run the action with a timeout
                try:
                    # We're using asyncio.wait_for here instead of the driver's with_timeout
                    # to better integrate with our context system
                    result = await asyncio.wait_for(
                        action.execute(driver, timeout_ctx),
                        timeout=timeout_ms / 1000  # Convert to seconds
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.debug(f"Action timed out after {timeout_ms}ms")
                    if on_timeout:
                        # Return default value from callback
                        try:
                            default_value = on_timeout()
                            return Ok(default_value)
                        except Exception as e:
                            return Error(Exception(f"Timeout handler failed: {e}"))
                    else:
                        # No default handler, propagate timeout as error
                        return Error(asyncio.TimeoutError(f"Action timed out after {timeout_ms}ms"))
            except Exception as e:
                return Error(e)
    
    return TimeoutAction()


def tap(main_action: Action[T], 
        side_effect: Action[Any]) -> Action[T]:
    """
    Execute a main action and a side effect action, returning the result of the main action.
    The side effect action is only executed if the main action succeeds.
    
    Args:
        main_action: The primary action whose result will be returned
        side_effect: Action to execute as a side effect if main action succeeds
        
    Returns:
        An Action that executes both actions but returns only the main action's result

    Example:
    ```
        # Log a value while continuing with main processing
        workflow = tap(
            main_action=GetText(".message"),
            side_effect=LogToConsole()
        )
    ```
    """
    
    class TapAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            ctx = context or ActionContext()
            
            try:
                # Execute the main action with the provided context
                main_result = await main_action.execute(driver, ctx)
                
                if main_result.is_error():
                    return main_result
                
                # Create a context for the side effect that includes the main result
                side_ctx = ActionContext(
                    retry_count=ctx.retry_count,
                    max_retries=ctx.max_retries,
                    retry_delay_ms=ctx.retry_delay_ms,
                    timeout_ms=ctx.timeout_ms,
                    parent_context=ctx,
                    metadata={
                        **ctx.metadata,
                        "tap_operation": "side_effect",
                        "tap_timestamp": datetime.now().isoformat(),
                        "tap_has_main_result": True
                    }
                )
                
                # Only execute side effect if main action succeeds
                # We ignore any errors from the side effect
                try:
                    await side_effect.execute(driver, side_ctx)
                except Exception as e:
                    logger.debug(f"Side effect action in tap failed: {e}")
                
                # Return the main action's result regardless of side effect result
                return main_result
            except Exception as e:
                return Error(e)
    
    return TapAction()


def log(message: str, level: str = "info") -> Action[None]:
    """
    Create an action that logs a message at the specified level.
    
    Args:
        message: Message to log
        level: Log level (debug, info, warning, error, critical)
        
    Returns:
        An Action that logs and returns None
    """
    
    class LogAction(Action[None]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
            ctx = context or ActionContext()
            
            try:
                log_fn = getattr(logger, level.lower())
                log_fn(message)
                return Ok(None)
            except Exception as e:
                return Error(e)
    
    return LogAction()


def wait(ms: int) -> Action[None]:
    """
    Create an action that waits for the specified number of milliseconds.
    
    Args:
        ms: Number of milliseconds to wait
        
    Returns:
        An Action that waits and returns None
    """
    
    class WaitAction(Action[None]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
            ctx = context or ActionContext()
            
            try:
                await asyncio.sleep(ms / 1000)
                return Ok(None)
            except Exception as e:
                return Error(e)
    
    return WaitAction()

