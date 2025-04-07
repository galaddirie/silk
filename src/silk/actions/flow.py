import asyncio
import logging
import random
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar, cast

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def branch(
    condition: Action[bool], if_true: Action[S], if_false: Optional[Action[S]] = None
) -> Action[S]:
    """
    Branch execution based on the result of a condition action.

    Args:
        condition: An action that determines which branch to take (must return bool)
        if_true: Action to execute if condition is True
        if_false: Optional action to execute if condition is False
                  If not provided, returns None when condition is False

    Returns:
        An Action that branches based on the condition result
    """

    class BranchAction(Action[S]):
        async def execute(self, context: ActionContext) -> Result[S, Exception]:
            try:
                branch_ctx = context.derive(
                    metadata={
                        "branch_operation": "condition",
                        "branch_timestamp": datetime.now().isoformat(),
                    }
                )

                condition_result = await condition.execute(branch_ctx)

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
                    logger.debug("Branch condition is True, taking if_true path")
                    return await if_true.execute(branch_path_ctx)
                elif if_false is not None:
                    logger.debug("Branch condition is False, taking if_false path")
                    return await if_false.execute(branch_path_ctx)
                else:
                    logger.debug("Branch condition is False, no if_false path provided")
                    return Ok(cast(S, None))
            except Exception as e:
                return Error(e)

    return BranchAction()


def loop_until(
    condition: Action[bool],
    body: Action[T],
    max_iterations: int = 10,
    delay_ms: int = 1000,
) -> Action[T]:
    """
    Repeatedly execute body action until condition succeeds or max_iterations is reached.

    Args:
        condition: Action that determines when to stop looping (must return bool)
        body: Action to execute in each iteration
        max_iterations: Maximum number of times to execute the action
        delay_ms: Delay between iterations in milliseconds

    Returns:
        An Action that loops until the condition is met
    """

    class LoopUntilAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                iterations = 0
                last_body_result: Optional[Result[T, Exception]] = None

                while iterations < max_iterations:
                    iter_ctx = context.derive(
                        metadata={
                            "loop_iteration": iterations + 1,
                            "loop_max_iterations": max_iterations,
                            "loop_timestamp": datetime.now().isoformat(),
                        }
                    )

                    body_result = await body.execute(iter_ctx)

                    if body_result.is_error():
                        return body_result

                    last_body_result = body_result

                    condition_result = await condition.execute(iter_ctx)

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


def retry(action: Action[T], max_attempts: int = 3, delay_ms: int = 1000) -> Action[T]:
    """
    Create a new action that retries the original action until it succeeds.

    This is a convenience function that wraps the Action.retry() method.

    Args:
        action: Action to retry
        max_attempts: Maximum number of attempts
        delay_ms: Delay between attempts in milliseconds

    Returns:
        A new Action with retry logic
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

    return RetryAction()


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

    return RetryWithBackoffAction()


# todo remove asyncio wait - some libraries this freezes network requests in the browser
def with_timeout(action: Action[T], timeout_ms: int) -> Action[T]:
    """
    Execute action with timeout. If timeout occurs, raise TimeoutError.

    Args:
        action: The action to execute with timeout
        timeout_ms: Timeout in milliseconds

    Returns:
        An Action with timeout constraint
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

    return WithTimeoutAction()


def with_timeout_and_fallback(
    action: Action[T], timeout_ms: int, on_timeout: Optional[Callable[[], T]] = None
) -> Action[T]:
    """
    Execute action with timeout. If timeout occurs, either raise
    TimeoutError or return result from on_timeout callback.

    Args:
        action: The action to execute with timeout
        timeout_ms: Timeout in milliseconds
        on_timeout: Optional callback to provide a default value on timeout

    Returns:
        An Action with timeout constraint
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
                    if on_timeout:
                        try:
                            default_value = on_timeout()
                            return Ok(default_value)
                        except Exception as e:
                            return Error(Exception(f"Timeout handler failed: {e}"))
                    else:
                        return Error(
                            asyncio.TimeoutError(
                                f"Action timed out after {timeout_ms}ms"
                            )
                        )
            except Exception as e:
                return Error(e)

    return TimeoutAction()


def tap(main_action: Action[T], side_effect: Action[Any]) -> Action[T]:
    """
    Execute a main action and a side effect action, returning the result of the main action.
    The side effect action is only executed if the main action succeeds.

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

                side_ctx = context.derive(
                    metadata={
                        "tap_operation": "side_effect",
                        "tap_timestamp": datetime.now().isoformat(),
                        "tap_has_main_result": True,
                    }
                )

                try:
                    await side_effect.execute(side_ctx)
                except Exception as e:
                    logger.debug(f"Side effect action in tap failed: {e}")

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
        async def execute(self, context: ActionContext) -> Result[None, Exception]:
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
        async def execute(self, context: ActionContext) -> Result[None, Exception]:
            try:
                await asyncio.sleep(ms / 1000)
                return Ok(None)
            except Exception as e:
                return Error(e)

    return WaitAction()
