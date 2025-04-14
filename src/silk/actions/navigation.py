"""
Navigation actions for browser movement, waiting for elements, and capturing screenshots.
"""

import logging
import asyncio
from pathlib import Path
from typing import Any, Optional, Union

from expression import Error, Ok, Result
from fp_ops import operation

from silk.actions.context import ActionContext
from silk.actions.utils import validate_driver
from silk.browsers.types import NavigationOptions, WaitOptions
from silk.selectors.selector import Selector, SelectorGroup

logger = logging.getLogger(__name__)


@operation(context=True, context_type=ActionContext)
async def Navigate(
    url: str, options: Optional[NavigationOptions] = None, **kwargs: Any
) -> Result[None, Exception]:
    """
    Action to navigate to a URL

    Args:
        url: URL to navigate to
        options: Additional navigation options
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
            await driver.goto(context.page_id, url)
            print(f"Navigated to {url}")
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GoBack(
    options: Optional[NavigationOptions] = None, **kwargs: Any
) -> Result[None, Exception]:
    """
    Action to navigate back in browser history

    Args:
        options: Additional navigation options
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
            await driver.go_back(context.page_id)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GoForward(
    options: Optional[NavigationOptions] = None, **kwargs: Any
) -> Result[None, Exception]:
    """
    Action to navigate forward in browser history

    Args:
        options: Additional navigation options
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
            await driver.go_forward(context.page_id)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Reload(
    options: Optional[NavigationOptions] = None, **kwargs: Any
) -> Result[None, Exception]:
    """
    Action to reload the current page

    Args:
        options: Additional navigation options
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
            await driver.reload(context.page_id)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def WaitForNavigation(
    options: Optional[NavigationOptions] = None, **kwargs: Any
) -> Result[None, Exception]:
    """
    Action to wait for a navigation to complete

    Args:
        options: Additional navigation options
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
            await driver.wait_for_navigation(context.page_id, options)
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def Screenshot(path: Path, **kwargs: Any) -> Result[Path, Exception]:
    """
    Action to take a screenshot

    Args:
        path: Path where to save the screenshot

    Returns:
        The path to the saved screenshot
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
            await driver.screenshot(context.page_id, path)
            return Ok(path)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetCurrentUrl(**kwargs: Any) -> Result[str, Exception]:
    """
    Action to get the current URL

    Returns:
        The current URL
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
            url_result = await driver.current_url(context.page_id)
            if url_result.is_error():
                return Error(url_result.error)
            url = url_result.default_value(None)
            if url is None:
                return Error(Exception("No URL found"))
            return Ok(url)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetPageSource(**kwargs: Any) -> Result[str, Exception]:
    """
    Action to get the page source

    Returns:
        The HTML source of the current page
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
            source_result = await driver.get_source(context.page_id)
            if source_result.is_error():
                return Error(source_result.error)
            source = source_result.default_value(None)
            if source is None:
                return Error(Exception("No source found"))
            return Ok(source)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def ExecuteScript(
    script: str, *args: Any, **kwargs: Any
) -> Result[Any, Exception]:
    """
    Action to execute JavaScript in the browser

    Args:
        script: JavaScript code to execute
        args: Arguments to pass to the script

    Returns:
        The return value of the script
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        # Extract args parameter if provided in kwargs
        script_args = args
        if "args" in kwargs:
            script_args = kwargs["args"]

        if context.page_id is not None:
            result = await driver.execute_script(context.page_id, script, *script_args)
            return Ok(result)
        else:
            return Error(Exception("No browser page found"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def WaitForSelector(
    selector: Union[str, Selector, SelectorGroup],
    options: Optional[WaitOptions] = None,
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Action to wait for a selector to appear in the page

    Args:
        selector: Selector to wait for
        options: Additional wait options
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)
        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        selector_value = selector
        if isinstance(selector, Selector):
            selector_value = selector.value
        elif isinstance(selector, SelectorGroup):
            # Use the first selector in the group
            if not selector.selectors:
                return Error(Exception("Empty selector group"))
            first_selector = selector.selectors[0]
            if isinstance(first_selector, Selector):
                selector_value = first_selector.value
            else:
                selector_value = first_selector

        if context.page_id is not None:
            await driver.wait_for_selector(
                context.page_id, str(selector_value), options
            )
            return Ok(None)
        else:
            return Error(Exception("No page ID found"))
    except Exception as e:
        return Error(e)
