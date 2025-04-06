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
)
from abc import ABC, abstractmethod
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

from functools import reduce, wraps
import asyncio
from silk.browsers.driver import BrowserDriver
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")

P = ParamSpec("P")  # Represents function parameters


class Action(ABC, Generic[T]):
    """
    Base class for all actions that can be performed in a browser
    
    An Action represents a pure operation that can be composed with
    other actions using functional programming patterns.
    """

    @abstractmethod
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
        """
        Execute the action using the given browser driver
        
        Args:
            driver: Browser driver to execute the action with
            context: Optional execution context with metadata
            
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
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
                ctx = context or ActionContext()
                result = await original_action.execute(driver, ctx)
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
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
                ctx = context or ActionContext()
                try:
                    # First execute the original action
                    result = await original_action.execute(driver, ctx)
                    
                    # If we have an error, return it directly
                    if result.is_error():
                        return cast(Result[S, Exception], result)
                    
                    # Get the next action using the result value
                    value = result.value if hasattr(result, 'value') else None
                    if value is None:
                        return Error(Exception("No value to chain to"))
                    next_action = f(value)
                    
                    # Execute the next action and return its result
                    return await next_action.execute(driver, ctx)
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
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
                ctx = context or ActionContext()
                ctx.max_retries = max_attempts
                ctx.retry_delay_ms = delay_ms
                
                last_error = None
                
                for attempt in range(max_attempts):
                    ctx.retry_count = attempt
                    try:
                        result = await original_action.execute(driver, ctx)
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
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
                ctx = context or ActionContext()
                ctx.timeout_ms = timeout_ms
                
                return await driver.with_timeout(
                    lambda d: original_action.execute(d, ctx),
                    timeout_ms
                )
        
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
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Union[T, S], Exception]:
                ctx = context or ActionContext()
                try:
                    result = await first_action.execute(driver, ctx)
                    if result.is_ok():
                        return result
                except Exception:
                    pass
                
                # First action failed, try the second
                return await second_action.execute(driver, ctx)
        
        return FallbackAction()
    
    def __and__(self, other: "Action[S]") -> "Action[Tuple[T, S]]":
        """
        Overload the & operator for parallel execution
        
        a & b means "execute actions a and b in parallel and return both results"
        """
        first_action = self
        second_action = other
        
        class ParallelAction(Action[Tuple[T, S]]):
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Tuple[T, S], Exception]:
                ctx = context or ActionContext()
                try:
                    # Execute both actions in parallel
                    results = await asyncio.gather(
                        first_action.execute(driver, ctx),
                        second_action.execute(driver, ctx),
                        return_exceptions=True
                    )
                    
                    # Check for exceptions
                    for result in results:
                        if isinstance(result, Exception):
                            return Error(result)
                    
                    # If both results are Ok, combine them
                    if all(hasattr(result, 'value') for result in results):
                        return Ok((results[0].value, results[1].value))
                    
                    # If any result is an Error, return the first error
                    for result in results:
                        if hasattr(result, 'error'):
                            return Error(result.error)
                    
                    # This should not happen, but just in case
                    return Error(Exception("Unexpected error in parallel execution"))
                except Exception as e:
                    return Error(e)
        
        return ParallelAction()
    
    def __call__(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Awaitable[Result[T, Exception]]:
        """
        Make Action instances callable directly with a driver
        
        This allows using actions like: result = await action(driver)
        """
        return self.execute(driver, context)

def unwrap(value: Union[Result[T, Exception], T, Exception]) -> T:
    """Unwrap a value from a Result if it's not already a Result"""
    if isinstance(value, Result):
        if value.is_ok():
            return cast(T, value.default_value(None))
        else:
            raise value.error
    elif isinstance(value, Exception):
        raise value
    return value

def wrap_result(value: Union[Result[T, Exception], T, Exception]) -> Result[T, Exception]:
    """Wrap a value in a Result if it's not already a Result"""
    if isinstance(value, Result):
        return value
    elif isinstance(value, Exception):
        return Error(value)
    else:
        return Ok(value)

def create_action(func: Callable[[BrowserDriver, Optional[ActionContext]], Awaitable[Result[T, Exception]]]) -> Action[T]:
    """
    Create an action from a function
    
    Args:
        func: Function that takes a driver and context and returns a Result
        
    Returns:
        An Action that wraps the function
    """
    
    class FunctionalAction(Action[T]):
        async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
            ctx = context or ActionContext()
            try:
                return await func(driver, ctx)
            except Exception as e:
                return Error(e)
    
    return FunctionalAction()
