from functools import wraps
import inspect
import logging
from typing import Any, Optional, TypeVar, Callable, Union, cast, Type, Dict, List, Awaitable, ParamSpec, overload, Generic

from expression.core import Result, Ok, Error
from silk.actions.base import Action, create_action
from silk.browsers.driver import BrowserDriver
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


def wrap_result(value: Union[Result[T, Exception], T, Exception]) -> Result[T, Exception]:
    """Wrap a value in a Result if it's not already a Result"""
    if isinstance(value, Result):
        return value
    elif isinstance(value, Exception):
        return Error(value)
    else:
        return Ok(value)


def action() -> Callable[[Callable[..., Any]], Callable[..., Action[Any]]]:
    """
    Decorator to convert a function into an Action.
    
    Makes it easy to create custom actions with proper railway-oriented error handling.
    Handles both synchronous and asynchronous functions.
        
    Returns:
        A decorator function that converts the decorated function to an Action
        
    Example:
        @action()
        async def custom_click(driver, selector):
            element = await driver.query_selector(selector)
            await element.click()
            return "clicked"
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Action[Any]]:
        is_async = inspect.iscoroutinefunction(func)
        sig = inspect.signature(func)
        has_context_param = 'context' in sig.parameters
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Action[Any]:
            class DecoratedAction(Action[Any]):
                async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
                    ctx = context or ActionContext()
                    try:
                        # Only pass context if the function expects it
                        if has_context_param:
                            kwargs['context'] = ctx
                            
                        if is_async:
                            result = await func(driver, *args, **kwargs)
                        else:
                            result = func(driver, *args, **kwargs)
                            
                        return wrap_result(result)
                    except Exception as e:
                        logger.debug(f"Error in action {func.__name__}: {e}")
                        return Error(e)
            
            return DecoratedAction()
        return wrapper  
    return decorator


def unwrap(func: Callable[P, Awaitable[Result[T, Exception]]]) -> Callable[P, Awaitable[T]]:
    """
    Decorator that automatically unwraps Result objects from element methods.
    
    This decorator transforms a function that returns a Result[T, Exception]
    into one that directly returns T, raising the exception if there was an error.
    
    Args:
        func: An async function that returns a Result
        
    Returns:
        An async function that returns the unwrapped value or raises an exception
    
    Example:
    ```python
        @unwrap
        async def get_text(element):
            return await element.get_text()  # Returns Result[str, Exception]
            
        # Now get_text returns str directly and raises exceptions
    ```
    """
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        result = await func(*args, **kwargs)
        
        if result.is_error():
            raise result.error if hasattr(result, 'error') else Exception(f"Unknown error in {func.__name__}")
            
        # Extract value from Result
        value = result.value if hasattr(result, 'value') else cast(T, result.default_value(None))
        
        if value is None:
            raise ValueError(f"Result from {func.__name__} contained None")
            
        return value
     
    return wrapper


def with_context(func: Callable[[T, ActionContext], S]) -> Callable[[T], Action[S]]:
    """
    Decorator to create an action that processes a value with access to the ActionContext.
    
    This is useful for creating transformation actions that need access to the context.
    
    Args:
        func: A function that takes a value and context and returns a new value
        
    Returns:
        A function that takes a value and returns an Action
    
    Example:
    ```python
        @with_context
        def add_metadata(value, context):
            return {**value, "metadata": context.metadata}
            
        # Usage: extract_data() >> add_metadata
    ```
    """
    def wrapper(value: T) -> Action[S]:
        class ContextAwareAction(Action[S]):
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
                ctx = context or ActionContext()
                try:
                    result = func(value, ctx)
                    return Ok(result)
                except Exception as e:
                    return Error(e)
        
        return ContextAwareAction()
    
    return wrapper


def transform(func: Callable[[T], S]) -> Callable[[T], Action[S]]:
    """
    Decorator to create a transformation action from a simple function.
    
    This is a shorthand for map() when you want to define a reusable transformation.
    
    Args:
        func: A function that takes a value and returns a transformed value
        
    Returns:
        A function that takes a value and returns an Action with the transformed value
    
    Example:
    ```python
        @transform
        def extract_prices(html):
            return re.findall(r'\$\d+.\d+', html)
            
        # Usage: get_html() >> extract_prices
    ```
    """
    def wrapper(value: T) -> Action[S]:
        class TransformAction(Action[S]):
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
                ctx = context or ActionContext()
                try:
                    result = func(value)
                    return Ok(result)
                except Exception as e:
                    return Error(e)
        
        return TransformAction()
    
    return wrapper


def log_result(label: Optional[str] = None, level: str = "info") -> Callable[[Action[T]], Action[T]]:
    """
    Decorator to log the result of an action without affecting the workflow.
    
    Args:
        label: Optional label to prepend to the log
        level: Log level (debug, info, warning, error)
        
    Returns:
        A decorator function that wraps an action with logging
    
    Example:
    ```python
        @log_result("Prices found")
        def extract_prices():
            # ... implementation ...
            
        # Or inline:
        get_html() >> log_result("HTML")(extract_prices)
    ```
    """
    def decorator(action: Action[T]) -> Action[T]:
        prefix = f"{label}: " if label else ""
        log_func = getattr(logger, level.lower())
        
        class LogResultAction(Action[T]):
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
                ctx = context or ActionContext()
                result = await action.execute(driver, ctx)
                
                if result.is_ok():
                    value = result.value if hasattr(result, 'value') else "No value"
                    log_func(f"{prefix}{value}")
                else:
                    error = result.error if hasattr(result, 'error') else "Unknown error"
                    log_func(f"{prefix}ERROR: {error}")
                
                return result
        
        return LogResultAction()
    
    return decorator


def retry_on_exception(exception_types: Union[Type[Exception], List[Type[Exception]]],
                       max_retries: int = 3,
                       delay_ms: int = 1000) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator that retries a function when specific exceptions occur.
    
    This is useful for element methods that may fail due to transient issues.
    
    Args:
        exception_types: Exception type(s) that should trigger retry
        max_retries: Maximum number of retry attempts
        delay_ms: Delay between retries in milliseconds
        
    Returns:
        A decorator function that adds retry logic to the decorated function
    
    Example:
    ```python
        @retry_on_exception([StaleElementException, TimeoutException], max_retries=3)
        async def click_element(element):
            await element.click()
    ```
    """
    import asyncio
    
    # Convert single exception to list
    if not isinstance(exception_types, list):
        exception_types = [exception_types]
    
    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Only retry if exception type matches
                    if any(isinstance(e, ex_type) for ex_type in exception_types):
                        last_exception = e
                        logger.debug(f"Retry attempt {attempt+1}/{max_retries} for {func.__name__}: {e}")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay_ms / 1000)
                    else:
                        # If exception doesn't match, don't retry
                        raise
            
            # If we get here, all retries failed
            raise last_exception or Exception(f"All {max_retries} retry attempts failed")
        
        return wrapper
    
    return decorator


def element_action(func: Callable[..., Awaitable[Result[T, Exception]]]) -> Callable[..., Action[T]]:
    """
    Decorator for creating an Action from an element method.
    
    This is useful for wrapping element methods into Actions for composition.
    
    Args:
        func: An element method that returns a Result
        
    Returns:
        A function that returns an Action
    
    Example:
    ```python
        @element_action
        async def get_text(element, selector):
            el = await element.query_selector(selector)
            return await el.get_text()
            
        # Usage: get_text(element, ".title")
    ```
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Action[T]:
        class ElementAction(Action[T]):
            async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
                ctx = context or ActionContext()
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    return Error(e)
        
        return ElementAction()
    
    return wrapper


def conditional_action(condition_fn: Callable[[T], bool]) -> Callable[[Action[S]], Callable[[T], Action[S]]]:
    """
    Creates a decorator that makes an action execute conditionally based on input.
    
    Args:
        condition_fn: Function that takes a value and returns True/False
        
    Returns:
        A decorator that makes the action execute only if condition is True
    
    Example:
    ```python
        @conditional_action(lambda text: "login" in text.lower())
        def handle_login_flow():
            # Only executed if condition is true
            ...
            
        # Usage: get_page_text() >> handle_login_flow
    ```
    """
    def decorator(action: Action[S]) -> Callable[[T], Action[S]]:
        def wrapper(value: T) -> Action[S]:
            class ConditionalAction(Action[S]):
                async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[S, Exception]:
                    ctx = context or ActionContext()
                    
                    try:
                        # Check if condition is true
                        if condition_fn(value):
                            return await action.execute(driver, ctx)
                        else:
                            # Skip this action, return None wrapped in Ok
                            return Ok(cast(S, None))
                    except Exception as e:
                        return Error(e)
            
            return ConditionalAction()
        
        return wrapper
    
    return decorator