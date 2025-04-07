import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, Union

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")
P = ParamSpec("P")

logger = logging.getLogger(__name__)


def wrap_result(
    value: Union[Result[T, Exception], T, Exception],
) -> Result[T, Exception]:
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
        async def custom_click(context, selector):
            page_result = await context.get_page()
            if page_result.is_error():
                return page_result
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))
            element_result = await page.query_selector(selector)
            if element_result.is_error():
                return element_result
            element = element_result.default_value(None)
            if element is None:
                return Error(Exception("Failed to get element"))
            return await element.click()
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Action[Any]]:
        is_async = inspect.iscoroutinefunction(func)
        sig = inspect.signature(func)
        has_context_param = "context" in sig.parameters

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Action[Any]:
            class DecoratedAction(Action[Any]):
                async def execute(
                    self, context: ActionContext
                ) -> Result[Any, Exception]:
                    try:
                        # Add context as the first argument if the function expects it
                        if has_context_param:
                            kwargs["context"] = context

                        if is_async:
                            result = await func(*args, **kwargs)
                        else:
                            result = func(*args, **kwargs)

                        return wrap_result(result)
                    except Exception as e:
                        logger.debug(f"Error in action {func.__name__}: {e}")
                        return Error(e)

            return DecoratedAction()

        return wrapper

    return decorator


def unwrap(
    func: Callable[P, Awaitable[Result[T, Exception]]],
) -> Callable[P, Awaitable[T]]:
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
            raise result.error

        value = result.default_value(None)

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
            async def execute(self, context: ActionContext) -> Result[S, Exception]:
                try:
                    result = func(value, context)
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
            return re.findall(r'...', html)

        # Usage: get_html() >> extract_prices
    ```
    """

    def wrapper(value: T) -> Action[S]:
        class TransformAction(Action[S]):
            async def execute(self, context: ActionContext) -> Result[S, Exception]:
                try:
                    result = func(value)
                    return Ok(result)
                except Exception as e:
                    return Error(e)

        return TransformAction()

    return wrapper


def async_action() -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Action[T]]]:
    """
    Decorator to convert an async function into an Action with proper error handling.

    Similar to @action() but specifically for async functions that don't return Results.

    Returns:
        A decorator function that converts an async function to an Action

    Example:
        @async_action()
        async def wait_and_get_data(seconds, url):
            await asyncio.sleep(seconds)
            # This will be automatically wrapped in Result
            return {"url": url, "timestamp": time.time()}
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Action[T]]:
        sig = inspect.signature(func)
        has_context_param = "context" in sig.parameters

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Action[T]:
            class AsyncAction(Action[T]):
                async def execute(self, context: ActionContext) -> Result[T, Exception]:
                    try:
                        # Add context as an argument if the function expects it
                        if has_context_param:
                            kwargs["context"] = context

                        result = await func(*args, **kwargs)
                        return Ok(result)
                    except Exception as e:
                        logger.debug(f"Error in async action {func.__name__}: {e}")
                        return Error(e)

            return AsyncAction()

        return wrapper

    return decorator
