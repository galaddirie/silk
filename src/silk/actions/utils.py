from typing import Any, Callable
from expression.core import Result, Ok, Error
from expression import pipe, Option

from silk.actions.base import Action
from silk.browser import BrowserDriver
from silk.selectors import Selector, SelectorGroup

# Helper function for element operations
async def _find_element_and_perform(
    driver: BrowserDriver, 
    selector: Selector, 
    action: Callable
) -> Result[None, Exception]:
    try:
        # Try CSS first if possible
        css_option = selector.to_css()
        
        if css_option.is_some():
            element = await driver.query_selector(css_option.unwrap())
            if element:
                await action(element)
                return Ok(None)
        
        # Fall back to XPath
        xpath = selector.to_xpath()
        element = await driver.query_selector(xpath)
        
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
    extract_fn: Callable
) -> Result[Any, Exception]:
    try:
        # Try CSS first if possible
        css_option = selector.to_css()
        
        if css_option.is_some():
            element = await driver.query_selector(css_option.unwrap())
            if element:
                result = await extract_fn(element)
                return Ok(result)
        
        # Fall back to XPath
        xpath = selector.to_xpath()
        element = await driver.query_selector(xpath)
        
        if element:
            result = await extract_fn(element)
            return Ok(result)
        else:
            return Error(Exception(f"Element not found: {selector}"))
    except Exception as e:
        return Error(e)
