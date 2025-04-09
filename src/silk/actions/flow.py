import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Callable, Generic, Optional, TypeVar, Union, cast, Protocol, runtime_checkable, Type

from expression.core import Error, Ok, Result

from silk.actions.base import Action, AdaptableAction
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def branch(
    condition: Union[Callable[[Any], bool], Action[bool]],
    if_true: Action[S],
    if_false: Optional[Action[S]] = None
) -> Union[Action[S], Callable[[Any], Action[S]]]:
    """
    Branch execution based on the result of a condition.
    
    This function can be used in two ways:
    1. With a condition Action that produces a boolean
    2. With a function that takes the input from a previous action and returns a boolean
    
    Examples:
    ```python
    # Using an Action that returns a boolean
    branch(element_exists("#popup"), Click("#close"), Continue())
    
    # Using a function in a composition chain
    Query(".price") >> ExtractText() >> 
        branch(
            lambda price: float(price.replace("$", "")) > 100, 
            Click("#premium"), 
            Click("#standard")
        )
    ```

    Args:
        condition: An action that determines which branch to take (must return bool)
                   or a function that takes a value and returns a boolean
        if_true: Action to execute if condition is True
        if_false: Optional action to execute if condition is False
                  If not provided, returns None when condition is False

    Returns:
        If condition is an Action: An Action that branches based on the condition result
        If condition is a function: A callable that returns an Action when given an input
    """
    if callable(condition) and not isinstance(condition, Action):
        def create_branch_action(input_value: Any) -> Action[S]:
            try:
                condition_result = condition(input_value)
                
                true_action = if_true
                if hasattr(if_true, 'with_input'):
                    true_action = if_true.with_input(input_value)
                    
                false_action = if_false
                if if_false is not None and hasattr(if_false, 'with_input'):
                    false_action = if_false.with_input(input_value)
                
                class InputBranchAction(Action[S]):
                    async def execute(self, context: ActionContext) -> Result[S, Exception]:
                        try:
                            branch_path_ctx = context.derive(
                                metadata={
                                    "branch_path": "true" if condition_result else "false",
                                    "branch_timestamp": datetime.now().isoformat(),
                                }
                            )

                            if condition_result:
                                return await true_action.execute(branch_path_ctx)
                            elif false_action is not None:
                                return await false_action.execute(branch_path_ctx)
                            else:
                                return Ok(cast(S, None))
                        except Exception as e:
                            return Error(e)
                
                return InputBranchAction()
            except Exception as e:
                class ErrorAction(Action[S]):
                    async def execute(self, context: ActionContext) -> Result[S, Exception]:
                        return Error(e)
                return ErrorAction()
        
        return create_branch_action
    
    # If condition is an Action, create and return a BranchAction
    condition_action = cast(Action[bool], condition)
    
    class BranchAction(Action[S]):
        async def execute(self, context: ActionContext) -> Result[S, Exception]:
            try:
                branch_ctx = context.derive(
                    metadata={
                        "branch_operation": "condition",
                        "branch_timestamp": datetime.now().isoformat(),
                    }
                )

                condition_result = await condition_action.execute(branch_ctx)

                if condition_result.is_error():
                    return Error(
                        Exception(f"Branch condition failed: {condition_result.error}")
                    )

                condition_value = condition_result.default_value(False)

                branch_path_ctx = context.derive(
                    metadata={
                        "branch_path": "true" if condition_value else "false",
                        "branch_timestamp": datetime.now().isoformat(),
                    }
                )

                if condition_value:
                    return await if_true.execute(branch_path_ctx)
                elif if_false is not None:
                    return await if_false.execute(branch_path_ctx)
                else:
                    return Ok(cast(S, None))
            except Exception as e:
                return Error(e)

    return BranchAction()

If = branch # Adding these aliases purely because i like how my IDE highlights them as variables instead of functions

def loop_until(
    condition: Union[Callable[[T], bool], Action[bool]],
    body: Action[T],
    max_iterations: int = 10,
    delay_ms: int = 1000,
    pass_result_to_next: bool = True
) -> Action[T]:
    """
    Repeatedly execute body action until condition succeeds or max_iterations is reached.
    
    This function can be used in two ways:
    1. With a condition Action that produces a boolean
    2. With a function that takes the result of the body action and returns a boolean
    
    Args:
        condition: Action that determines when to stop looping (must return bool)
                  or a function that takes the body result and returns a boolean
        body: Action to execute in each iteration
        max_iterations: Maximum number of times to execute the action
        delay_ms: Delay between iterations in milliseconds
        pass_result_to_next: Whether to pass the result of each iteration to the next
                            (True: functional state passing, False: just repeat action)

    Returns:
        An Action that loops until the condition is met
    """

    class LoopUntilAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                iterations = 0
                last_body_result: Optional[Result[T, Exception]] = None
                last_value: Any = None

                while iterations < max_iterations:
                    iter_ctx = context.derive(
                        metadata={
                            "loop_iteration": iterations + 1,
                            "loop_max_iterations": max_iterations,
                            "loop_timestamp": datetime.now().isoformat(),
                        }
                    )
                    
                    # If we're passing results between iterations and have a previous result,
                    # adapt the body action to use the previous result if possible
                    current_body = body
                    if pass_result_to_next and iterations > 0 and last_value is not None and hasattr(body, 'with_input'):
                        current_body = body.with_input(last_value)

                    body_result = await current_body.execute(iter_ctx)

                    if body_result.is_error():
                        return body_result

                    last_body_result = body_result
                    last_value = body_result.default_value(None)

                    # Handle the condition based on its type
                    condition_result: Result[bool, Exception]
                    
                    if callable(condition) and not isinstance(condition, Action):
                        # If condition is a function, apply it to the body result
                        try:
                            condition_value = condition(last_value)
                            condition_result = Ok(condition_value)
                        except Exception as e:
                            condition_result = Error(e)
                    else:
                        # If condition is an Action, execute it
                        condition_action = cast(Action[bool], condition)
                        # If the condition action can adapt to the body result, do so
                        if hasattr(condition_action, 'with_input'):
                            condition_action = condition_action.with_input(last_value)
                        condition_result = await condition_action.execute(iter_ctx)

                    if condition_result.is_error():
                        iterations += 1
                        if iterations < max_iterations:
                            logger.debug(
                                f"Loop condition check failed, iteration {iterations}/{max_iterations}"
                            )
                            await asyncio.sleep(delay_ms / 1000)
                        continue

                    condition_value = condition_result.default_value(False)

                    if condition_value:
                        logger.debug(
                            f"Loop condition met at iteration {iterations + 1}"
                        )
                        return last_body_result

                    iterations += 1
                    if iterations < max_iterations:
                        logger.debug(
                            f"Loop condition not met, iteration {iterations}/{max_iterations}"
                        )
                        await asyncio.sleep(delay_ms / 1000)
                    else:
                        logger.debug(f"Reached max iterations ({max_iterations})")

                return Error(
                    Exception(
                        f"Maximum iterations ({max_iterations}) reached in loop_until"
                    )
                )
            except Exception as e:
                return Error(e)

    return LoopUntilAction()

LoopUntil = loop_until

def retry(action: Action[T], max_attempts: int = 3, delay_ms: int = 1000) -> Action[T]:
    """
    Create a new action that retries the original action until it succeeds.
    
    This function preserves the input/output relationship of the original action,
    passing any inputs through to the retried action.

    Args:
        action: Action to retry
        max_attempts: Maximum number of attempts
        delay_ms: Delay between attempts in milliseconds

    Returns:
        A new Action with retry logic that preserves input adaptation
    """

    class RetryAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            retry_context = context.derive(
                max_retries=max_attempts, retry_delay_ms=delay_ms
            )

            last_error = None

            for attempt in range(max_attempts):
                attempt_context = retry_context.derive(retry_count=attempt)

                try:
                    result = await action.execute(attempt_context)
                    if result.is_ok():
                        return result
                    last_error = result.error
                except Exception as e:
                    last_error = e

                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay_ms / 1000)

            return Error(last_error or Exception(f"All {max_attempts} attempts failed"))
            
        def with_input(self, value: Any) -> Action[T]:
            """Allow the retry action to adapt to inputs by passing them to the inner action"""
            if hasattr(action, 'with_input'):
                adapted_action = action.with_input(value)
                return retry(adapted_action, max_attempts, delay_ms)
            return self

    return RetryAction()

Retry = retry

def retry_with_backoff(
    action: Action[T],
    max_attempts: int = 3,
    initial_delay_ms: int = 1000,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    should_retry: Optional[Callable[[Exception], bool]] = None,
) -> Action[T]:
    """
    Retry action with exponential backoff and optional jitter.
    
    This function preserves the input/output relationship of the original action,
    passing any inputs through to the retried action.

    Args:
        action: The action to retry
        max_attempts: Maximum number of retry attempts
        initial_delay_ms: Initial delay between retries in milliseconds
        backoff_factor: Multiplier for delay after each retry
        jitter: Add randomness to delay to prevent thundering herd
        should_retry: Optional function to determine if specific errors should trigger retry

    Returns:
        An Action with retry logic that preserves input adaptation
    """

    class RetryWithBackoffAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                last_error = None
                delay: float = float(initial_delay_ms)

                for attempt in range(max_attempts):
                    retry_ctx = context.derive(
                        retry_count=attempt,
                        max_retries=max_attempts,
                        retry_delay_ms=int(delay),
                        metadata={
                            "backoff_attempt": attempt + 1,
                            "backoff_max_attempts": max_attempts,
                            "backoff_delay_ms": delay,
                            "backoff_timestamp": datetime.now().isoformat(),
                        },
                    )

                    try:
                        result = await action.execute(retry_ctx)
                        if result.is_ok():
                            return result

                        last_error = result.error

                        if should_retry and not should_retry(last_error):
                            logger.debug(f"Error not eligible for retry: {last_error}")
                            return result

                    except Exception as e:
                        last_error = e
                        if should_retry and not should_retry(e):
                            logger.debug(f"Exception not eligible for retry: {e}")
                            return Error(e)

                    if attempt < max_attempts - 1:
                        current_delay: float = delay
                        if jitter:
                            jitter_factor = random.uniform(0.8, 1.2)
                            current_delay = delay * jitter_factor

                        logger.info(
                            f"Retry {attempt+1}/{max_attempts} failed, waiting {current_delay: .0f}ms"
                        )
                        await asyncio.sleep(current_delay / 1000)

                        delay = delay * backoff_factor

                return Error(
                    last_error
                    or Exception(f"Action failed after {max_attempts} retry attempts")
                )
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[T]:
            """Allow the retry action to adapt to inputs by passing them to the inner action"""
            if hasattr(action, 'with_input'):
                adapted_action = action.with_input(value)
                return retry_with_backoff(
                    adapted_action, 
                    max_attempts, 
                    initial_delay_ms, 
                    backoff_factor, 
                    jitter, 
                    should_retry
                )
            return self

    return RetryWithBackoffAction()

RetryWithBackoff = retry_with_backoff

def with_timeout(action: Action[T], timeout_ms: int) -> Action[T]:
    """
    Execute action with timeout. If timeout occurs, raise TimeoutError.
    
    This function preserves the input/output relationship of the original action,
    passing any inputs through to the timed action.

    Args:
        action: The action to execute with timeout
        timeout_ms: Timeout in milliseconds

    Returns:
        An Action with timeout constraint that preserves input adaptation
    """

    class WithTimeoutAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                timeout_ctx = context.derive(
                    timeout_ms=timeout_ms,
                    metadata={
                        "timeout_ms": timeout_ms,
                        "timeout_timestamp": datetime.now().isoformat(),
                    },
                )

                try:
                    result = await asyncio.wait_for(
                        action.execute(timeout_ctx),
                        timeout=timeout_ms / 1000,
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.debug(f"Action timed out after {timeout_ms}ms")
                    return Error(
                        asyncio.TimeoutError(f"Action timed out after {timeout_ms}ms")
                    )
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[T]:
            """Allow the timeout action to adapt to inputs by passing them to the inner action"""
            if hasattr(action, 'with_input'):
                adapted_action = action.with_input(value)
                return with_timeout(adapted_action, timeout_ms)
            return self

    return WithTimeoutAction()

WithTimeout = with_timeout

def with_timeout_and_fallback(
    action: Action[T], 
    timeout_ms: int, 
    on_timeout: Union[T, Callable[[], T], Action[T]]
) -> Action[T]:
    """
    Execute action with timeout. If timeout occurs, either provide a default value
    or execute a fallback action.
    
    This function preserves the input/output relationship of the original action,
    passing any inputs through to the timed action.

    Args:
        action: The action to execute with timeout
        timeout_ms: Timeout in milliseconds
        on_timeout: Default value, callback to provide a default value, or fallback action

    Returns:
        An Action with timeout constraint that preserves input adaptation
    """

    class TimeoutAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            timeout_ctx = context.derive(
                timeout_ms=timeout_ms,
                metadata={
                    "timeout_ms": timeout_ms,
                    "timeout_timestamp": datetime.now().isoformat(),
                },
            )

            try:
                try:
                    result = await asyncio.wait_for(
                        action.execute(timeout_ctx),
                        timeout=timeout_ms / 1000,
                    )
                    return result
                except asyncio.TimeoutError:
                    logger.debug(f"Action timed out after {timeout_ms}ms")
                    
                    if isinstance(on_timeout, Action):
                        # If on_timeout is an Action, execute it
                        return await on_timeout.execute(
                            context.derive(
                                metadata={
                                    "timeout_fallback": "action",
                                    "timeout_ms": timeout_ms,
                                }
                            )
                        )
                    elif callable(on_timeout) and not isinstance(on_timeout, Action):
                        # If on_timeout is a function, call it
                        try:
                            default_value = on_timeout()
                            return Ok(default_value)
                        except Exception as e:
                            return Error(Exception(f"Timeout handler failed: {e}"))
                    else:
                        # Otherwise, treat on_timeout as a constant value
                        return Ok(cast(T, on_timeout))
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[T]:
            """Allow the timeout action to adapt to inputs by passing them to the inner action"""
            if hasattr(action, 'with_input'):
                adapted_action = action.with_input(value)
                
                # Also adapt the fallback if it's an action
                adapted_fallback = on_timeout
                if isinstance(on_timeout, Action) and hasattr(on_timeout, 'with_input'):
                    adapted_fallback = on_timeout.with_input(value)
                    
                return with_timeout_and_fallback(adapted_action, timeout_ms, adapted_fallback)
            return self

    return TimeoutAction()

WithTimeoutAndFallback = with_timeout_and_fallback

def tap(main_action: Action[T], side_effect: Action[Any]) -> Action[T]:
    """
    Execute a main action and a side effect action, returning the result of the main action.
    The side effect action is only executed if the main action succeeds.
    
    The main action's result is passed to the side effect if it can accept it.
    
    Args:
        main_action: The primary action whose result will be returned
        side_effect: Action to execute as a side effect if main action succeeds

    Returns:
        An Action that executes both actions but returns only the main action's result
    """

    class TapAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                main_result = await main_action.execute(context)

                if main_result.is_error():
                    return main_result
                    
                main_value = main_result.default_value(None)

                side_ctx = context.derive(
                    metadata={
                        "tap_operation": "side_effect",
                        "tap_timestamp": datetime.now().isoformat(),
                        "tap_has_main_result": True,
                    }
                )
                
                # If side_effect can adapt to the main result, do so
                current_side_effect = side_effect
                if hasattr(side_effect, 'with_input'):
                    current_side_effect = side_effect.with_input(main_value)

                try:
                    await current_side_effect.execute(side_ctx)
                except Exception as e:
                    logger.debug(f"Side effect action in tap failed: {e}")

                return main_result
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[T]:
            """Allow the tap action to adapt to inputs by passing them to both actions"""
            adapted_main = main_action
            if hasattr(main_action, 'with_input'):
                adapted_main = main_action.with_input(value)
                
            adapted_side = side_effect
            if hasattr(side_effect, 'with_input'):
                adapted_side = side_effect.with_input(value)
                
            return tap(adapted_main, adapted_side)

    return TapAction()

Tap = tap

def log(message: str, level: str = "info") -> Action[None]:
    """
    Create an action that logs a message at the specified level.
    
    This action can be used as a logging tap in a composition chain.
    It preserves any input passed to it for further composition.

    Args:
        message: Message to log (can include {value} placeholder for input value)
        level: Log level (debug, info, warning, error, critical)

    Returns:
        An Action that logs and returns None, but passes input forward via with_input
    """

    class LogAction(Action[None]):
        def __init__(self, message: str, level: str = "info", value_to_log: Any = None):
            self.message = message
            self.level = level
            self.value_to_log = value_to_log
            
        async def execute(self, context: ActionContext) -> Result[None, Exception]:
            try:
                log_fn = getattr(logger, self.level.lower())
                
                # If we have a value and the message contains {value}, format the message
                final_message = self.message
                if self.value_to_log is not None and "{value}" in self.message:
                    try:
                        final_message = self.message.format(value=self.value_to_log)
                    except Exception:
                        # If formatting fails, just use the original message
                        pass
                        
                log_fn(final_message)
                return Ok(None)
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[Any]:
            """Create a new LogAction that will log the value and pass it through"""
            return LogAndContinue(self.message, self.level, value)

    # Special action that logs but returns the input value (for use in composition chains)
    class LogAndContinue(Action[Any]):
        def __init__(self, message: str, level: str = "info", value: Any = None):
            self.message = message
            self.level = level
            self.value = value
            
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                log_fn = getattr(logger, self.level.lower())
                
                # If we have a value and the message contains {value}, format the message
                final_message = self.message
                if self.value is not None and "{value}" in self.message:
                    try:
                        final_message = self.message.format(value=self.value)
                    except Exception:
                        # If formatting fails, just use the original message
                        pass
                        
                log_fn(final_message)
                return Ok(self.value)
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[Any]:
            """Create a new LogAndContinue with the updated value"""
            return LogAndContinue(self.message, self.level, value)

    return LogAction(message, level)

Log = log

def wait(ms: int) -> Action[None]:
    """
    Create an action that waits for the specified number of milliseconds.
    
    This action can be used in a composition chain and will pass any
    input it receives to the next action in the chain.

    Args:
        ms: Number of milliseconds to wait

    Returns:
        An Action that waits and preserves input for further composition
    """

    class WaitAction(Action[None]):
        def __init__(self, ms: int, value_to_pass: Any = None):
            self.ms = ms
            self.value_to_pass = value_to_pass
            
        async def execute(self, context: ActionContext) -> Result[None, Exception]:
            try:
                await asyncio.sleep(self.ms / 1000)
                return Ok(None)
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[Any]:
            """Create a wait action that passes the value through"""
            return WaitAndContinue(self.ms, value)

    # Special action that waits but returns the input value
    class WaitAndContinue(Action[Any]):
        def __init__(self, ms: int, value: Any = None):
            self.ms = ms
            self.value = value
            
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                await asyncio.sleep(self.ms / 1000)
                return Ok(self.value)
            except Exception as e:
                return Error(e)
                
        def with_input(self, value: Any) -> Action[Any]:
            """Create a new WaitAndContinue with the updated value"""
            return WaitAndContinue(self.ms, value)

    return WaitAction(ms)

Wait = wait


