from typing import Any, Callable, Optional, Tuple, Union, TypeVar, cast

from expression import Error, Result, Ok
from silk.browsers.models import ActionContext, ElementHandle, Driver, Page, CoordinateType, MouseOptions
from silk.selectors import Selector, SelectorGroup

T = TypeVar('T')


async def resolve_target(
    context: ActionContext, 
    target: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType]
) -> Result[ElementHandle, Exception]:
    page = context.page
    
    if page is None:
        return Error(Exception("No page found"))
    
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
        
        element = element_result.default_value(cast(ElementHandle, None))
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

async def validate_driver(context: ActionContext) -> Result[Driver, Exception]:
    """Helper function to validate and retrieve the driver"""
    driver = context.driver
    if driver is None:
        return Error(Exception("No driver found"))
    
    if context.page_id is None:
        return Error(Exception("No page found"))
    
    return Ok(driver)


async def get_element_coordinates(
    target: Union[ElementHandle, CoordinateType], 
    options: Optional[MouseOptions] = None
) -> Result[Tuple[float, float], Exception]:
    """Helper function to get coordinates from an element or coordinate tuple"""
    # Handle tuple directly without using isinstance with a generic type
    if isinstance(target, tuple) and len(target) == 2:  # Coordinate type
        return Ok((float(target[0]), float(target[1])))
    
    result = await target.get_bounding_box()
    if result.is_error():
        return Error(result.error)
    
    bounding_box = result.default_value(None)
    if bounding_box is None:
        return Error(Exception("No bounding box found"))
    
    x, y = bounding_box["x"], bounding_box["y"]
    
    if options and options.move_to_center:
        x += bounding_box["width"] / 2
        y += bounding_box["height"] / 2
    
    return Ok((float(x), float(y)))

