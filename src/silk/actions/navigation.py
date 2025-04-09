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
