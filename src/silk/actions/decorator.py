from silk.actions.base import create_action, Action
from silk.browser.driver import BrowserDriver
from expression.core import Result, Ok, Error

from functools import wraps
import inspect
from typing import Any, Optional, TypeVar, Callable, Union, cast, Type, Dict, List

T = TypeVar('T')

def action(name: Optional[str] = None, description: Optional[str] = None) -> Callable[[Callable], Callable[..., Action[Any]]]:
    """
    Decorator to convert a function into an Action.
    
    Makes it easy to create custom actions with proper railway-oriented error handling.
    Handles both synchronous and asynchronous functions.
    
    Args:
        name: Optional name for the action (defaults to function name)
        description: Optional description of what the action does
        
    Returns:
        A decorator function that converts the decorated function to an Action
        
    Example:
        @action("custom_click")
        async def custom_click(driver, selector):
            element = await driver.query_selector(selector)
            await element.click()
            return "clicked"
    """
    def decorator(func: Callable) -> Callable[..., Action[Any]]:
        is_async = inspect.iscoroutinefunction(func)
        action_name = name or func.__name__
        action_description = description or func.__doc__
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Action[Any]:
            # Create a closure over the args and kwargs
            async def execute_fn(driver: BrowserDriver) -> Result[Any, Exception]:
                try:
                    if is_async:
                        result = await func(driver, *args, **kwargs)
                    else:
                        result = func(driver, *args, **kwargs)
                    
                    # If the function already returns a Result, return it directly
                    if isinstance(result, Result):
                        return result
                    
                    # Otherwise wrap the result in Ok
                    return Ok(result)
                except Exception as e:
                    return Error(e)
            
            return create_action(
                name=f"{action_name}({', '.join([str(a) for a in args])})",
                execute_fn=execute_fn,
                description=action_description
            )
        
        return wrapper
    
    return decorator


