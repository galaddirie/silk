from typing import Any, Callable, Optional, Tuple, Union, TypeVar

from expression import Error, Result, Ok
from silk.actions.context import ActionContext
from silk.browsers.driver import  BrowserDriver
from silk.browsers.element import ElementHandle
from silk.selectors import Selector, SelectorGroup

T = TypeVar('T')

async def resolve_target(
    context: ActionContext, 
    target: Union[str, Selector, SelectorGroup, ElementHandle, Tuple[int, int]]
) -> Result[ElementHandle, Exception]:
    page_result = await context.get_page()
    if page_result.is_error():
        return Error(page_result.error)
    
    page = page_result.default_value(None)
    if page is None:
        return Error(Exception("No browser page found"))
    
    if isinstance(target, str):
        element_result = await page.query_selector(target)
        if element_result.is_error():
            return Error(element_result.error)
        
        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("No element found"))
        return Ok(element)
    
    if isinstance(target, Selector):
        element_result = await page.query_selector(target.value)
        if element_result.is_error():
            return Error(element_result.error)
        
        element = element_result.default_value(None)
        if element is None:
            return Error(Exception("No element found"))
        return Ok(element)
    
    if isinstance(target, SelectorGroup):
        for selector in target.selectors:
            element_result = await resolve_target(context, selector)
            element = element_result.default_value(None)
            if element is not None:
                return Ok(element)
        return Error(Exception("No element found"))
    
    if isinstance(target, ElementHandle):
        return Ok(target)
    
    # If we get here, it's not a valid target
    return Error(Exception(f"Unsupported target type: {type(target)}"))

async def validate_driver(context: ActionContext) -> Result[BrowserDriver, Exception]:
    """Helper function to validate and retrieve the driver"""
    driver_result = await context.get_driver()
    if driver_result.is_error():
        return Error(driver_result.error)
    
    driver = driver_result.default_value(None)
    if driver is None:
        return Error(Exception("No browser driver found"))
    
    if context.page_id is None:
        return Error(Exception("No browser page found"))
    
    return Ok(driver)


async def get_element_coordinates(
    target: Union[ElementHandle, Tuple[int, int]], 
    options: Optional[Any] = None
) -> Result[Tuple[float, float], Exception]:
    """Helper function to get coordinates from an element or coordinate tuple"""
    # Handle tuple directly without using isinstance with a generic type
    if isinstance(target, tuple) and len(target) == 2:  # Coordinate type
        return Ok((float(target[0]), float(target[1])))
    
    # Element handle
    result = await target.get_bounding_box()
    if result.is_error():
        return Error(result.error)
    
    bounding_box = result.default_value(None)
    if bounding_box is None:
        return Error(Exception("No bounding box found"))
    
    x, y = bounding_box["x"], bounding_box["y"]
    
    if options and getattr(options, "move_to_center", False):
        x += bounding_box["width"] / 2
        y += bounding_box["height"] / 2
    
    return Ok((float(x), float(y)))

