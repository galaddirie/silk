"""
Navigation actions for browser movement, waiting for elements, and capturing screenshots.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, Union, cast

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.models.browser import ActionContext, NavigationOptions, WaitOptions
from silk.selectors.selector import Selector, SelectorGroup, SelectorType

logger = logging.getLogger(__name__)


class Navigate(Action[None]):
    """
    Action to navigate to a URL

    Args:
        url: URL to navigate to
        options: Additional navigation options
    """

    def __init__(self, url: str, options: Optional[NavigationOptions] = None):
        self.url = url
        self.options = options or NavigationOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Navigate to the specified URL"""
        try:
            logger.debug(f"Navigating to {self.url}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.goto(self.url, self.options)
        except Exception as e:
            logger.error(f"Error navigating to {self.url}: {e}")
            return Error(e)


class GoBack(Action[None]):
    """
    Action to navigate back in browser history

    Args:
        options: Additional navigation options
    """

    def __init__(self, options: Optional[NavigationOptions] = None):
        self.options = options or NavigationOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Navigate back in browser history"""
        try:
            logger.debug("Navigating back in history")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.go_back()
        except Exception as e:
            logger.error(f"Error navigating back: {e}")
            return Error(e)


class GoForward(Action[None]):
    """
    Action to navigate forward in browser history

    Args:
        options: Additional navigation options
    """

    def __init__(self, options: Optional[NavigationOptions] = None):
        self.options = options or NavigationOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Navigate forward in browser history"""
        try:
            logger.debug("Navigating forward in history")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.go_forward()
        except Exception as e:
            logger.error(f"Error navigating forward: {e}")
            return Error(e)


class Reload(Action[None]):
    """
    Action to reload the current page

    Args:
        options: Additional navigation options
    """

    def __init__(self, options: Optional[NavigationOptions] = None):
        self.options = options or NavigationOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Reload the current page"""
        try:
            logger.debug("Reloading page")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.reload()
        except Exception as e:
            logger.error(f"Error reloading page: {e}")
            return Error(e)


class WaitForSelector(Action[Any]):
    """
    Action to wait for an element to appear in the DOM

    Args:
        selector: Element selector to wait for
        options: Additional wait options

    Returns:
        The found element if successful
    """

    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup],
        options: Optional[WaitOptions] = None,
    ):
        self.selector = selector
        self.options = options or WaitOptions()

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"

    async def execute(self, context: ActionContext) -> Result[Any, Exception]:
        """Wait for selector to match an element in the DOM"""
        try:
            logger.debug(f"Waiting for selector {self.selector_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        result = await self._wait_for_selector(selector, page)
                        if result.is_ok():
                            return result
                    except Exception:
                        pass

                return Error(
                    Exception(f"No selector in group matched: {self.selector.name}")
                )
            else:
                selector = (
                    self.selector
                    if isinstance(self.selector, Selector)
                    else Selector(type=cast(SelectorType, "css"), value=self.selector)
                )
                return await self._wait_for_selector(selector, page)

        except Exception as e:
            logger.error(f"Error waiting for selector {self.selector_desc}: {e}")
            return Error(e)

    async def _wait_for_selector(
        self, selector: Selector, page: Any
    ) -> Result[Any, Exception]:
        """Helper method to wait for a specific selector"""
        try:
            timeout = self.options.timeout or selector.timeout

            options = self._create_driver_options(timeout)

            element_result = await page.wait_for_selector(selector.value, options)
            if element_result.is_error():
                return Error(element_result.error)
            return Ok(element_result.default_value(None))
        except Exception as e:
            return Error(e)

    def _create_driver_options(self, timeout: Optional[int]) -> WaitOptions:
        """Create options object with the right timeout"""
        options_dict = (
            self.options.model_dump()
            if hasattr(self.options, "model_dump")
            else self.options.dict()
        )
        if timeout is not None:
            options_dict["timeout"] = timeout
        return WaitOptions(**options_dict)


class WaitForNavigation(Action[None]):
    """
    Action to wait for a navigation to complete

    Args:
        options: Additional navigation options
    """

    def __init__(self, options: Optional[NavigationOptions] = None):
        self.options = options or NavigationOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Wait for navigation to complete"""
        try:
            wait_until = self.options.wait_until
            logger.debug(
                f"Waiting for navigation to complete (wait_until={wait_until})"
            )

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.wait_for_navigation(self.options)
        except Exception as e:
            logger.error(f"Error waiting for navigation: {e}")
            return Error(e)


class WaitForFunction(Action[Any]):
    """
    Action to wait for a JavaScript function to return true

    Args:
        function_body: JavaScript function body or expression that evaluates to true/false
        polling: Polling interval in milliseconds
        timeout: Timeout in milliseconds

    Returns:
        The return value of the function when it evaluates to true
    """

    def __init__(self, function_body: str, polling: int = 100, timeout: int = 30000):
        self.function_body = function_body
        self.polling = polling
        self.timeout = timeout

    async def execute(self, context: ActionContext) -> Result[Any, Exception]:
        """Wait for function to evaluate to true"""
        try:
            logger.debug(
                f"Waiting for function to return true (timeout={self.timeout}ms)"
            )

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            is_expression = (
                not self.function_body.strip().startswith("function")
                and "{" not in self.function_body
            )

            if is_expression:
                script = rf"return () => {self.function_body};"
            else:
                script = rf"return {self.function_body};"

            func_result = await page.execute_script(script)
            if func_result.is_error():
                return func_result

            start_time = asyncio.get_event_loop().time()

            while True:
                current_time = asyncio.get_event_loop().time()
                if (current_time - start_time) * 1000 > self.timeout:
                    return Error(
                        Exception(f"Wait for function timed out after {self.timeout}ms")
                    )

                result = await page.execute_script("return (arguments[0])();")
                if result.is_error():
                    return result

                value = result.default_value(None)
                if value is not None and value:
                    return result

                await asyncio.sleep(self.polling / 1000)

        except Exception as e:
            logger.error(f"Error waiting for function: {e}")
            return Error(e)


class Screenshot(Action[Path]):
    """
    Action to take a screenshot

    Args:
        path: Path where to save the screenshot

    Returns:
        The path to the saved screenshot
    """

    def __init__(self, path: Path):
        self.path = path

    async def execute(self, context: ActionContext) -> Result[Path, Exception]:
        """Take a screenshot and save it to the specified path"""
        try:
            logger.debug(f"Taking screenshot and saving to {self.path}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            self.path.parent.mkdir(parents=True, exist_ok=True)

            result = await page.screenshot(self.path)
            if result.is_error():
                return Error(result.error)

            return Ok(self.path)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return Error(e)


class GetCurrentUrl(Action[str]):
    """
    Action to get the current URL

    Returns:
        The current URL
    """

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        """Get the current URL"""
        try:
            logger.debug("Getting current URL")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            url_result = await page.current_url()
            if url_result.is_error():
                return Error(url_result.error)

            return Ok(url_result.default_value(""))
        except Exception as e:
            logger.error(f"Error getting current URL: {e}")
            return Error(e)


class GetPageSource(Action[str]):
    """
    Action to get the page source

    Returns:
        The HTML source of the current page
    """

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        """Get the HTML source of the current page"""
        try:
            logger.debug("Getting page source")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            source_result = await page.get_page_source()
            if source_result.is_error():
                return Error(source_result.error)

            return Ok(source_result.default_value(""))
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return Error(e)


class ExecuteScript(Action[Any]):
    """
    Action to execute JavaScript in the browser

    Args:
        script: JavaScript code to execute
        args: Arguments to pass to the script

    Returns:
        The return value of the script
    """

    def __init__(self, script: str, *args: Any):
        self.script = script
        self.args = args

    async def execute(self, context: ActionContext) -> Result[Any, Exception]:
        """Execute JavaScript code in the browser"""
        try:
            logger.debug(f"Executing script: {self.script[:50]}...")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            return await page.execute_script(self.script, *self.args)
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return Error(e)
