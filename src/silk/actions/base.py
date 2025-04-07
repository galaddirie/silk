from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Dict,
    List,
    Tuple,
    Optional,
    Protocol,
    Awaitable,
    Union,
    overload,
    cast,
    ParamSpec,
    TYPE_CHECKING
)
from abc import ABC, abstractmethod
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

from functools import reduce, wraps
import asyncio
import logging
from datetime import datetime

from silk.models.browser import ActionContext

if TYPE_CHECKING:
    from silk.browsers.manager import BrowserManager

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")

P = ParamSpec("P")  # Represents function parameters

logger = logging.getLogger(__name__)

class Action(ABC, Generic[T]):
    """
    Base class for all actions that can be performed in a browser
    
    An Action represents a pure operation that can be composed with
    other actions using functional programming patterns.
    """

    @abstractmethod
    async def execute(self, context: ActionContext) -> Result[T, Exception]:
        """
        Execute the action using the given context
        
        Args:
            context: Execution context with references to browser and page
            
        Returns:
            Result containing either the action result or an exception
        """
        pass
    
    def map(self, f: Callable[[T], S]) -> "Action[S]":
        """
        Create a new action that maps the result of this action
        
        Args:
            f: Function to transform the result
            
        Returns:
            A new Action with transformed result
        """
        original_action = self
        
        class MappedAction(Action[S]):
            async def execute(self, context: ActionContext) -> Result[S, Exception]:
                result = await original_action.execute(context)
                try:
                    return result.map(f)
                except Exception as e:
                    return Error(e)
        
        return MappedAction()
    
    def and_then(self, f: Callable[[T], "Action[S]"]) -> "Action[S]":
        """
        Chain an action after this one, using the result of this action
        
        Args:
            f: Function that takes the result of this action and returns a new action
            
        Returns:
            A new Action that chains the two actions
        """
        original_action = self
        
        class ChainedAction(Action[S]):
            async def execute(self, context: ActionContext) -> Result[S, Exception]:
                try:
                    # First execute the original action
                    result = await original_action.execute(context)
                    
                    # If we have an error, return it directly
                    if result.is_error():
                        return cast(Result[S, Exception], result)
                    
                    # Get the next action using the result value
                    value = result.default_value(None)
                    if value is None:
                        return Error(Exception("No value to chain to"))
                    next_action = f(value)
                    
                    # Execute the next action with the same context
                    return await next_action.execute(context)
                except Exception as e:
                    return Error(e)
        
        return ChainedAction()
    
    def retry(self, max_attempts: int = 3, delay_ms: int = 1000) -> "Action[T]":
        """
        Create a new action that retries this action multiple times until it succeeds
        
        Args:
            max_attempts: Maximum number of retry attempts
            delay_ms: Delay between retries in milliseconds
            
        Returns:
            A new Action with retry logic
        """
        original_action = self
        
        class RetryAction(Action[T]):
            async def execute(self, context: ActionContext) -> Result[T, Exception]:
                # Create retry-specific context
                retry_context = context.derive(
                    max_retries=max_attempts,
                    retry_delay_ms=delay_ms
                )
                
                last_error = None
                
                for attempt in range(max_attempts):
                    # Update retry count for each attempt
                    attempt_context = retry_context.derive(retry_count=attempt)
                    
                    try:
                        result = await original_action.execute(attempt_context)
                        if result.is_ok():
                            return result
                        last_error = result.error if hasattr(result, 'error') else None
                    except Exception as e:
                        last_error = e
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay_ms / 1000)
                
                return Error(
                    last_error or Exception(f"All {max_attempts} attempts failed")
                )
        
        return RetryAction()
    
    def with_timeout(self, timeout_ms: int) -> "Action[T]":
        """
        Create a new action that times out after the specified duration
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            A new Action with timeout logic
        """
        original_action = self
        
        class TimeoutAction(Action[T]):
            async def execute(self, context: ActionContext) -> Result[T, Exception]:
                # Create timeout-specific context
                timeout_context = context.derive(timeout_ms=timeout_ms)
                
                try:
                    # Run the action with a timeout
                    result = await asyncio.wait_for( # todo this might block the event loop and prevent the browser from doing anything else in some driver implementations
                        original_action.execute(timeout_context),
                        timeout=timeout_ms / 1000  # Convert to seconds
                    )
                    
                    return result
                except asyncio.TimeoutError:
                    return Error(Exception(f"Operation timed out after {timeout_ms}ms"))
                except Exception as e:
                    return Error(e)
        
        return TimeoutAction()
    
    def __rshift__(
        self, other: Union[Callable[[T], S], "Action[Any]"]
    ) -> "Action[Any]":
        """
        Overload the >> operator for pipe-like sequencing
        
        a >> b is equivalent to:
        - If b is a function: a.map(b)
        - If b is an Action: a.and_then(lambda _: b)
        """
        if isinstance(other, Action):
            # Sequence actions: a >> b means "do a, then do b (ignoring a's result)"
            return self.and_then(lambda _: other)
        else:
            # Apply function to result: a >> f means "do a, then apply f to result"
            return self.map(other)
    
    def __or__(self, other: "Action[S]") -> "Action[Union[T, S]]":
        """
        Overload the | operator for fallback behavior
        
        a | b means "try action a, if it fails, try action b"
        """
        first_action = self
        second_action = other
        
        class FallbackAction(Action[Union[T, S]]):
            async def execute(self, context: ActionContext) -> Result[Union[T, S], Exception]:
                try:
                    # Create a fallback-specific metadata
                    fallback_context = context.derive(
                        metadata={"fallback_operation": "trying_first"}
                    )
                    
                    # Try the first action
                    result = await first_action.execute(fallback_context)
                    if result.is_ok():
                        return result
                except Exception:
                    pass
                
                # First action failed, try the second with updated metadata
                fallback_context = context.derive(
                    metadata={"fallback_operation": "trying_second"}
                )
                return await second_action.execute(fallback_context)
        
        return FallbackAction()
    
    def __and__(self, other: "Action[S]") -> "Action[Tuple[T, S]]":
        """
        Overload the & operator for parallel execution
        
        a & b means "execute actions a and b in parallel with separate contexts"
        """
        first_action = self
        second_action = other
        
        class ParallelAction(Action[Tuple[T, S]]):
            async def execute(self, context: ActionContext) -> Result[Tuple[T, S], Exception]:
                if not context.browser_manager:
                    return Error(Exception("Cannot execute parallel actions without a browser manager"))
                
                # Create two new contexts for the parallel actions
                first_context_id, second_context_id = None, None
                
                try:
                    # Create first context
                    context_result1 = await context.browser_manager.create_context()
                    if context_result1.is_error():
                        return Error(context_result1.error)
                    browser_context1 = context_result1.default_value(None)
                    if browser_context1 is None:
                        return Error(Exception("Failed to create first context"))
                    first_context_id = browser_context1.id
                    
                    # Get default page for first context
                    page_result1 = browser_context1.get_page()
                    if page_result1.is_error():
                        return Error(page_result1.error)
                    page1 = page_result1.default_value(None)
                    if page1 is None:
                        return Error(Exception("Failed to get first page"))
                    
                    # Create action context for first action
                    action_context1 = context.derive(
                        context_id=browser_context1.id,
                        page_id=page1.id,
                        metadata={"parallel_execution": "first_action"}
                    )
                    
                    # Create second context
                    context_result2 = await context.browser_manager.create_context()
                    if context_result2.is_error():
                        return Error(context_result2.error)
                    browser_context2 = context_result2.default_value(None)
                    if browser_context2 is None:
                        return Error(Exception("Failed to create second context"))
                    second_context_id = browser_context2.id
                    
                    # Get default page for second context
                    page_result2 = browser_context2.get_page()
                    if page_result2.is_error():
                        return Error(page_result2.error)
                    page2 = page_result2.default_value(None)
                    if page2 is None:
                        return Error(Exception("Failed to get second page"))
                    
                    # Create action context for second action
                    action_context2 = context.derive(
                        context_id=browser_context2.id,
                        page_id=page2.id,
                        metadata={"parallel_execution": "second_action"}
                    )
                    
                    results = await asyncio.gather(
                        first_action.execute(action_context1),
                        second_action.execute(action_context2),
                    )
                    
                    if any(isinstance(r, Exception) for r in results):
                        for r in results:
                            if isinstance(r, Exception):
                                return Error(r)
                    
                    result1, result2 = results[0], results[1]
                    
                    if result1.is_error():
                        return cast(Result[Tuple[T, S], Exception], Error(result1.error))
                    if result2.is_error():
                        return cast(Result[Tuple[T, S], Exception], Error(result2.error))
                    
                    
                    return Error(Exception("Unexpected error in parallel execution"))
                except Exception as e:
                    return Error(e)
                finally:
                    # Clean up the contexts
                    if first_context_id and context.browser_manager:
                        await context.browser_manager.close_context(first_context_id)
                    if second_context_id and context.browser_manager:
                        await context.browser_manager.close_context(second_context_id)
        
        return ParallelAction()
    
    def __call__(self, browser_manager: 'BrowserManager') -> Awaitable[Result[T, Exception]]:
        """
        Make Action instances callable directly with a browser manager
        
        This allows using actions like: result = await action(browser_manager)
        """
        return self.execute_with_manager(browser_manager)
    
    async def execute_with_manager(self, browser_manager: 'BrowserManager') -> Result[T, Exception]:
        """Execute this action using a BrowserManager to create a new context"""
        # Create a new context for this execution
        context_result = await browser_manager.create_context()
        if context_result.is_error():
            return Error(context_result.error)
        browser_context = context_result.default_value(None)
        if browser_context is None:
            return Error(Exception("Failed to create context"))
        
        try:
            # Get the default page
            page_result = browser_context.get_page()
            if page_result.is_error():
                return Error(page_result.error)
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))
            
            # Create an ActionContext
            action_context = ActionContext(
                browser_manager=browser_manager,
                context_id=browser_context.id,
                page_id=page.id
            )
            
            # Execute the action with the context
            return await self.execute(action_context)
        finally:
            # Always clean up the browser context
            await browser_manager.close_context(browser_context.id)


def create_action(func: Callable[[ActionContext], Awaitable[Result[T, Exception]]]) -> Action[T]:
    """
    Create an action from a function
    
    Args:
        func: Function that takes a context and returns a Result
        
    Returns:
        An Action that wraps the function
    """
    
    class FunctionalAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            try:
                return await func(context)
            except Exception as e:
                return Error(e)
    
    return FunctionalAction()