"""
Actions are the building blocks of Silk.

They represent pure operations that can be composed together using functional
programming patterns. Each action returns a Result type that handles both success
and error cases.

Silk provides several ways to compose actions:

- sequence: Executes actions in sequence and returns ALL results as a Block
- compose: Executes actions in sequence and returns ONLY the LAST result
- pipe: Creates a pipeline where each action can use the result of the previous action
- parallel: Executes actions concurrently and collects all results
- fallback: Tries actions in sequence until one succeeds

These can also be used through operators:
- a >> b: Equivalent to compose(a, b)
- a | b: Equivalent to fallback(a, b)
- a & b: Similar to parallel(a, b) but returns a tuple of results
"""

from typing import Union, Optional, Callable, Any, TypeVar, Generic

from silk.actions.mouse import (
    Click,
    MouseDown,
    MouseUp,
    MouseMove,
    MouseDoubleClick,
    MouseClick,
    Drag,
)
from silk.actions.keyboard import Type, KeyDown, KeyUp, KeyPress, TypeText, Shortcut
from silk.actions.extract import ExtractText, ExtractAttribute, ExtractMultiple
from silk.actions.base import (
    Action,
    create_action,
)
from silk.actions.composition import (
    parallel,
    pipe,
    compose,
    sequence,
    fallback,
)
from silk.actions.decorator import action
from silk.actions.control import (
    branch,
    loop_until,
    retry_with_backoff,
    with_timeout,
    tap,
)
from silk.selectors import Selector, SelectorGroup

# Re-export the base types
from expression.core import Result, Ok, Error, Option, Some, Nothing
from expression.collections import Block

# Add a generic type parameter for use with ExtractMultiple
T = TypeVar("T")


def click(selector: Union[Selector, SelectorGroup]) -> Action[None]:
    """Create a click action for the given selector"""
    return Click(selector)


def type_text(selector: Union[Selector, SelectorGroup], text: str) -> Action[None]:
    """Create a type action for the given selector and text"""
    return Type(selector, text)


def extract_text(selector: Union[Selector, SelectorGroup]) -> Action[str]:
    """Extract text from the given selector with railway-oriented error handling"""
    return ExtractText(selector)


def extract_attribute(
    selector: Union[Selector, SelectorGroup], attribute: str
) -> Action[Optional[str]]:
    """Extract an attribute from the given selector with railway-oriented error handling"""
    return ExtractAttribute(selector, attribute)


def extract_multiple(
    selector: Union[Selector, SelectorGroup],
    extract_fn: Optional[Callable[[], T]] = None,
) -> Action[Block[T]]:
    """Extract multiple elements matching the selector as an immutable Block"""
    if extract_fn:
        return ExtractMultiple(selector, extract_fn)
    return ExtractMultiple(selector)


def mouse_move(
    target: Union[Selector, SelectorGroup], offset_x: int = 0, offset_y: int = 0
) -> Action[None]:
    """Move mouse to the target (selector or coordinates)"""
    return MouseMove(target, offset_x, offset_y)


def drag(
    source: Union[Selector, SelectorGroup],
    target: Union[Selector, SelectorGroup],
    source_offset_x: int = 0,
    source_offset_y: int = 0,
    target_offset_x: int = 0,
    target_offset_y: int = 0,
) -> Action[None]:
    """Drag from source to target"""
    return Drag(
        source,
        target,
        source_offset_x,
        source_offset_y,
        target_offset_x,
        target_offset_y,
    )


def keyboard_shortcut(*keys: str) -> Action[None]:
    """Execute a keyboard shortcut with the given keys"""
    return Shortcut(*keys)


def key_press(key: str) -> Action[None]:
    """Press a key"""
    return KeyPress(key)


def retry(action: Action[T], max_attempts: int = 3, delay_ms: int = 1000) -> Action[T]:
    """
    Create a new action that retries the original action multiple times
    with railway-oriented error handling
    """
    return action.retry(max_attempts, delay_ms)


__all__ = [
    # Action classes
    "Action",
    "Click",
    "Type",
    "ExtractText",
    "ExtractAttribute",
    "ExtractMultiple",
    "MouseDown",
    "MouseUp",
    "MouseMove",
    "MouseDoubleClick",
    "MouseClick",
    "KeyDown",
    "KeyUp",
    "KeyPress",
    "TypeText",
    "Shortcut",
    "Drag",
    # Factory functions
    "click",
    "type_text",
    "extract_text",
    "extract_attribute",
    "extract_multiple",
    "mouse_move",
    "drag",
    "keyboard_shortcut",
    "key_press",
    "retry",
    # Control flow
    "branch",
    "loop_until",
    "retry_with_backoff",
    "with_timeout",
    "tap",
    # Combinators
    "parallel",
    "pipe",
    "compose",
    "create_action",
    "sequence",
    "fallback",
    "action",  # Add the action decorator
    # Expression types
    "Result",
    "Ok",
    "Error",
    "Option",
    "Some",
    "Nothing",
    "Block",
]
