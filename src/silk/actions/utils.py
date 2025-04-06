from typing import Any, Callable, TypeVar, Generic, Awaitable
from expression.core import Result, Ok, Error
from expression import pipe, Option

from silk.actions.base import Action
from silk.browsers import BrowserDriver
from silk.selectors import Selector, SelectorGroup

T = TypeVar('T')

# Helper function for element operations
async def _find_element_and_perform(
    driver: BrowserDriver, 
    selector: Selector, 
    action: Callable
) -> Result[None, Exception]:
    try:
     
        element = await driver.query_selector(selector.value)
        if element:
            await action(element)
            return Ok(None)
        
        
        else:
            return Error(Exception(f"Element not found: {selector}"))
    except Exception as e:
        return Error(e)
    

async def _find_element_and_extract(
    driver: BrowserDriver,
    selector: Selector,
    extract_fn: Callable[[Any], Awaitable[T]]
) -> Result[T, Exception]:
    try:
          
        element = await driver.query_selector(selector.value)
        if element:
            result = await extract_fn(element)
            return Ok(result)
        
        else:
            return Error(Exception(f"Element not found: {selector}"))
    except Exception as e:
        return Error(e)
