import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, Union, get_type_hints, Optional, Type, cast, Dict, Protocol, runtime_checkable

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


# Define a protocol for action factory functions
@runtime_checkable
class ActionFactory(Protocol[T]):
    """Protocol for action factory functions"""
    def __call__(self, **kwargs: Any) -> Action[T]: ...
    action_class: Type[Action[T]]
    original_func: Callable[..., Any]
    is_action_factory: bool
    input_param: Optional[str]


def action(
    function: Optional[Callable[..., Any]] = None,
    name: Optional[str] = None,
    input_param: Optional[str] = None,
    auto_adapt: bool = True,
    description: Optional[str] = None
) -> Union[ActionFactory[Any], Callable[[Callable[..., Any]], ActionFactory[Any]]]:
    """
    Decorator to transform a function into an Action.
    
    This decorator can be used in two ways:
    
    1. As a simple decorator:
       @action
       def my_function(context, param1, param2='default'):
           # function body
           
    2. With configuration options:
       @action(name="CustomName", input_param="param1", description="Does something")
       def my_function(context, param1, param2='default'):
           # function body
    
    The decorated function:
    - Must accept a context as its first parameter
    - Can have additional parameters (optional or required)
    - Can be synchronous or asynchronous
    - Can return a Result or a regular value (which will be wrapped in Ok)
    
    Args:
        function: The function to decorate
        name: Optional custom name for the Action
        input_param: Parameter name that should receive input from previous actions
                     If None, will try to determine automatically
        auto_adapt: Whether to automatically adapt to inputs from previous actions
        description: Optional description for the Action
    
    Returns:
        A factory function that creates instances of an Action class
    """
    def decorator(func: Callable[..., Any]) -> ActionFactory[Any]:
        # Get function signature and parameters
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        
        # Extract parameter information
        has_context_param = len(params) > 0 and params[0].name != 'self'
        
        # Figure out which parameter should accept input from previous actions
        adapt_param = input_param
        if adapt_param is None and auto_adapt and len(params) > 1:
            # Default to the first parameter after context
            adapt_param = params[1].name
        
        # Get return type hint if available
        extracted_return_type: Any = Any
        try:
            hints = get_type_hints(func)
            if 'return' in hints:
                return_hint = hints['return']
                # If it's a Result, extract the value type
                if hasattr(return_hint, '__origin__') and return_hint.__origin__ is Result:
                    if hasattr(return_hint, '__args__'):
                        extracted_return_type = return_hint.__args__[0]
                else:
                    extracted_return_type = return_hint
        except (TypeError, ValueError):
            pass
            
        # Create the Action class
        class FunctionAction(Action[Any]):
            def __init__(self, **kwargs: Any) -> None:
                self.kwargs: Dict[str, Any] = kwargs
                # Set default values for missing parameters with defaults
                for p in params[1:]:  # Skip context parameter
                    if p.default is not inspect.Parameter.empty and p.name not in self.kwargs:
                        self.kwargs[p.name] = p.default
                
            async def execute(self, context: ActionContext) -> Result[Any, Exception]:
                try:
                    # Prepare arguments
                    args = [context]
                    
                    # Call the function
                    is_async = inspect.iscoroutinefunction(func)
                    
                    if is_async:
                        result = await func(*args, **self.kwargs)
                    else:
                        result = func(*args, **self.kwargs)
                    
                    # Process the result
                    if isinstance(result, Result):
                        return result
                    else:
                        return Ok(result)
                except Exception as e:
                    return Error(e)
            
            def with_input(self, value: Any) -> Action[Any]:
                """Create a new action with the input applied to the specified parameter"""
                if not auto_adapt or adapt_param is None:
                    return self
                    
                # Create a new instance with the adapted parameter
                new_kwargs = dict(self.kwargs)
                new_kwargs[adapt_param] = value
                return FunctionAction(**new_kwargs)
            
            def __str__(self) -> str:
                action_name = name or func.__name__
                param_str = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
                return f"{action_name}({param_str})"
                
            def __repr__(self) -> str:
                return self.__str__()
                
        # Set metadata on the class
        FunctionAction.__name__ = name or func.__name__ + "Action"
        FunctionAction.__doc__ = description or func.__doc__
        
        # Create a factory function to instantiate the action
        @wraps(func)
        def factory(**kwargs: Any) -> Action[Any]:
            return FunctionAction(**kwargs)
            
        # Attach metadata for introspection
        # Use cast to help mypy understand these attributes will exist
        typed_factory = cast(ActionFactory[Any], factory)
        typed_factory.action_class = FunctionAction
        typed_factory.original_func = func
        typed_factory.is_action_factory = True
        typed_factory.input_param = adapt_param
        
        return typed_factory
    
    # Handle case where decorator is used without parentheses
    if function is not None:
        return decorator(function)
    
    return decorator


def inputs(*param_names: str) -> Callable[[ActionFactory[Any]], ActionFactory[Any]]:
    """
    Decorator to specify which parameters should receive inputs from previous actions.
    
    Use with @action to customize input handling:
    
    @action
    @inputs('selector', 'text')
    def custom_action(context, selector, text):
        # This action will create adapters for both 'selector' and 'text'
        # parameters based on inputs from previous actions
    
    Args:
        *param_names: Names of parameters that should adapt to inputs
        
    Returns:
        A decorator that adds input handling logic
    """
    def decorator(factory_func: ActionFactory[Any]) -> ActionFactory[Any]:
        if not hasattr(factory_func, 'is_action_factory'):
            raise TypeError("@inputs can only be used with @action")
            
        original_create = factory_func
        
        @wraps(original_create)
        def wrapped_factory(**kwargs: Any) -> Action[Any]:
            original_action = original_create(**kwargs)
            
            # Instead of replacing the method, create a wrapper class
            class InputAdapterAction(Action[Any]):
                def __init__(self, wrapped_action: Action[Any]):
                    self.wrapped_action = wrapped_action
                
                async def execute(self, context: ActionContext) -> Result[Any, Exception]:
                    return await self.wrapped_action.execute(context)
                
                def with_input(self, value: Any) -> Action[Any]:
                    if value is None:
                        return self
                    
                    new_kwargs = dict(kwargs)
                    
                    # Try to match the value to the first parameter
                    if len(param_names) > 0:
                        new_kwargs[param_names[0]] = value
                        
                    return original_create(**new_kwargs)
                
                def __str__(self) -> str:
                    return str(self.wrapped_action)
                
                def __repr__(self) -> str:
                    return repr(self.wrapped_action)
            
            # Return the wrapped action
            return InputAdapterAction(original_action)
            
        # Add metadata to wrapped factory
        typed_wrapped = cast(ActionFactory[Any], wrapped_factory)
        typed_wrapped.original_func = factory_func.original_func
        typed_wrapped.is_action_factory = True
        typed_wrapped.action_class = factory_func.action_class
        typed_wrapped.input_param = None
        
        # Store param_names as an attribute
        setattr(typed_wrapped, 'input_params', param_names)
        
        return typed_wrapped
        
    return decorator