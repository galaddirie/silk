"""
Input actions for interacting with elements via mouse or keyboard in the browser.
"""

import logging
from typing import Any, List, Optional, Tuple, TypeVar, Union

from expression import Error, Ok, Result
from fp_ops import operation

from silk.actions.context import ActionContext
from silk.actions.utils import get_element_coordinates, resolve_target, validate_driver
from silk.browsers.element import ElementHandle
from silk.browsers.types import (
    DragOptions,
    KeyModifier,
    MouseButtonLiteral,
    MouseOptions,
    SelectOptions,
    TypeOptions,
)
from silk.selectors.selector import Selector, SelectorGroup

logger = logging.getLogger(__name__)

T = TypeVar("T")


@operation(context=True, context_type=ActionContext)
async def MouseMove(
    target: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]],
    offset_x: int = 0,
    offset_y: int = 0,
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to move the mouse to an element or specific coordinates

    Args:
        target: Target selector, element, or coordinates
        offset_x: X offset from target
        offset_y: Y offset from target
        options: Additional movement options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if isinstance(target, tuple) and len(target) == 2:
            x_float, y_float = float(target[0]), float(target[1])
        else:
            element_result = await resolve_target(context, target)
            element = element_result.default_value(None)
            if element is None:
                return Error(Exception("Target not found"))

            coords_result = await get_element_coordinates(element, options)
            if coords_result.is_error():
                return Error(coords_result.error)

            x_float, y_float = coords_result.default_value((0.0, 0.0))

            x_float += offset_x
            y_float += offset_y

        if context.page_id is not None:
            await driver.mouse_move(context.page_id, x_float, y_float)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Click(
    target: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]],
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to click an element

    Args:
        target: Target selector, element, or coordinates
        options: Additional click options
    """
    context: ActionContext = kwargs["context"]

    driver_result = await validate_driver(context)
    if driver_result.is_error():
        return Error(driver_result.error)
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))

    try:
        if isinstance(target, tuple) and len(target) == 2:
            x_int, y_int = int(target[0]), int(target[1])
            if context.page_id is not None:
                await driver.mouse_move(context.page_id, x_int, y_int, options)
                await driver.mouse_click(context.page_id, "left", options)
                return Ok(None)
            else:
                return Error(Exception("No page ID found"))

        element_result = await resolve_target(context, target)
        if element_result.is_error():
            return Error(element_result.error)

        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("Target not found"))

        selector = element.get_selector()
        if not selector:
            return Error(Exception("Target has no selector"))

        if context.page_id is not None:
            await driver.click(context.page_id, selector, options)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def DoubleClick(
    target: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]],
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to double-click an element

    Args:
        target: Target selector, element, or coordinates
        options: Additional click options
    """
    context: ActionContext = kwargs["context"]

    driver_result = await validate_driver(context)
    if driver_result.is_error():
        return Error(driver_result.error)
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))

    try:
        if isinstance(target, tuple) and len(target) == 2:
            x_int, y_int = int(target[0]), int(target[1])
            if context.page_id is not None:
                await driver.mouse_move(context.page_id, x_int, y_int, options)
                await driver.mouse_double_click(context.page_id, x_int, y_int, options)
                return Ok(None)
            else:
                return Error(Exception("No page ID found"))

        element_result = await resolve_target(context, target)
        if element_result.is_error():
            return Error(element_result.error)

        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("Target not found"))

        selector = element.get_selector()
        if not selector:
            return Error(Exception("Target has no selector"))

        if context.page_id is not None:
            await driver.double_click(context.page_id, selector, options)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def MouseDown(
    button: MouseButtonLiteral = "left",
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to press a mouse button

    Args:
        button: Mouse button to press
        options: Additional mouse options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if context.page_id is not None:
            await driver.mouse_down(context.page_id, button, options)
        else:
            return Error(Exception("No page ID found"))

        return Ok(None)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def MouseUp(
    button: MouseButtonLiteral = "left",
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to release a mouse button

    Args:
        button: Mouse button to release
        options: Additional mouse options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if context.page_id is not None:
            await driver.mouse_up(context.page_id, button, options)
        else:
            return Error(Exception("No page ID found"))

        return Ok(None)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Drag(
    source: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]],
    target: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]],
    options: Optional[DragOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to drag from one element/position to another

    Args:
        source: Source element or position
        target: Target element or position
        options: Additional drag options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if isinstance(source, tuple) and len(source) == 2:
            source_x, source_y = int(source[0]), int(source[1])
        else:
            source_element_result = await resolve_target(context, source)
            if source_element_result.is_error():
                return Error(source_element_result.error)

            source_element = source_element_result.default_value(None)
            if source_element is None:
                return Error(Exception("Source not found"))

            source_coords = await get_element_coordinates(source_element, options)
            if source_coords.is_error():
                return Error(source_coords.error)

            source_x_float, source_y_float = source_coords.default_value((0.0, 0.0))
            source_x, source_y = int(source_x_float), int(source_y_float)

        if isinstance(target, tuple) and len(target) == 2:
            target_x, target_y = int(target[0]), int(target[1])
        else:
            target_element_result = await resolve_target(context, target)
            if target_element_result.is_error():
                return Error(target_element_result.error)

            target_element = target_element_result.default_value(None)
            if target_element is None:
                return Error(Exception("Target not found"))

            target_coords = await get_element_coordinates(target_element, options)
            if target_coords.is_error():
                return Error(target_coords.error)

            target_x_float, target_y_float = target_coords.default_value((0.0, 0.0))
            target_x, target_y = int(target_x_float), int(target_y_float)

        if context.page_id is not None:
            await driver.mouse_drag(
                context.page_id, (source_x, source_y), (target_x, target_y), options
            )
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Fill(
    target: Union[str, Selector, SelectorGroup, ElementHandle],
    text: str,
    options: Optional[TypeOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to fill an input field with text

    Args:
        target: Target input element
        text: Text to input
        options: Additional typing options
    """
    context: ActionContext = kwargs["context"]

    driver_result = await validate_driver(context)
    if driver_result.is_error():
        return Error(driver_result.error)
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))

    if context.page_id is None:
        return Error(Exception("No page ID found"))

    try:
        element_result = await resolve_target(context, target)
        if element_result.is_error():
            return Error(element_result.error)

        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("Target not found"))

        selector = element.get_selector()
        if not selector:
            return Error(Exception("Target has no selector"))

        await driver.fill(context.page_id, selector, text, options)
        return Ok(None)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Type(
    target: Union[str, Selector, SelectorGroup, ElementHandle],
    text: str,
    options: Optional[TypeOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to type text (alias for Fill with more intuitive name)

    Args:
        target: Target input element
        text: Text to type
        options: Additional typing options
    """
    context: ActionContext = kwargs["context"]

    driver_result = await validate_driver(context)
    if driver_result.is_error():
        return Error(driver_result.error)
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))

    try:
        element_result = await resolve_target(context, target)
        if element_result.is_error():
            return Error(element_result.error)

        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("Target not found"))

        selector = element.get_selector()
        if not selector:
            return Error(Exception("Target has no selector"))

        if context.page_id is not None:
            await driver.type(context.page_id, selector, text, options)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def KeyPress(
    key: str,
    modifiers: Optional[List[KeyModifier]] = None,
    options: Optional[TypeOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to press a key or key combination

    Args:
        key: Key or key combination to press
        modifiers: List of keyboard modifiers to apply
        options: Additional key press options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        actual_options: Optional[TypeOptions] = None

        if modifiers is not None:
            actual_options = TypeOptions(modifiers=modifiers)
        else:
            actual_options = options

        if context.page_id is not None:
            await driver.key_press(context.page_id, key, actual_options)
        else:
            return Error(Exception("No page ID found"))

        return Ok(None)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Select(
    target: Union[str, Selector, SelectorGroup, ElementHandle],
    value: Optional[str] = None,
    text: Optional[str] = None,
    options: Optional[SelectOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to select an option from a dropdown

    Args:
        target: Target select element
        value: Option value to select
        text: Option text to select (alternative to value)
        options: Additional select options
    """
    context: ActionContext = kwargs["context"]

    driver_result = await validate_driver(context)
    if driver_result.is_error():
        return Error(driver_result.error)
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))

    try:
        element_result = await resolve_target(context, target)
        if element_result.is_error():
            return Error(element_result.error)

        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("Target not found"))

        selector = element.get_selector()
        if not selector:
            return Error(Exception("Target has no selector"))

        if context.page_id is not None:
            await driver.select(context.page_id, selector, value, text)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Scroll(
    target: Optional[Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]]] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    options: Optional[MouseOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to scroll the page to an element or specific coordinates

    Args:
        target: Target selector, element, or coordinates to scroll to
        x: X coordinate to scroll to (alternative to target)
        y: Y coordinate to scroll to (alternative to target)
        options: Additional scrolling options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if context.page_id is None:
            return Error(Exception("No page ID found"))

        # If target is specified, scroll to the element
        if target is not None:
            if isinstance(target, tuple) and len(target) == 2:
                x_int, y_int = int(target[0]), int(target[1])
                return await driver.scroll(context.page_id, x=x_int, y=y_int)
            else:
                element_result = await resolve_target(context, target)
                if element_result.is_error():
                    return Error(element_result.error)

                element = element_result.default_value(None)
                if element is None:
                    return Error(Exception("Target not found"))

                selector = element.get_selector()
                if not selector:
                    return Error(Exception("Target has no selector"))

                # Scroll element into view
                return await driver.scroll(context.page_id, selector=selector)
        # If coordinates are specified, scroll to the position
        elif x is not None or y is not None:
            return await driver.scroll(context.page_id, x=x, y=y)
        else:
            return Error(Exception("Either target or scroll coordinates (x, y) must be specified"))

    except Exception as e:
        return Error(e)
