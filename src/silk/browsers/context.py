import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from expression import Error, Ok, Result
from fp_ops import BaseContext
from pydantic import Field

if TYPE_CHECKING:
    from silk.browsers.driver import BrowserDriver
    from silk.browsers.element import ElementHandle
    from silk.browsers.manager import BrowserManager
    from silk.browsers.types import (
        CoordinateType,
        DragOptions,
        MouseButtonLiteral,
        MouseOptions,
        NavigationOptions,
        TypeOptions,
        WaitOptions,
    )

logger = logging.getLogger(__name__)



class BrowserPage:
    """
    Represents a single page (tab) in a browser context

    This is a wrapper around the driver page object
    it provides a more user friendly api for the user

    Attributes:
        id: The id of the page
        context_id: The id of the context
        driver: The driver object
        page_ref: The native page object from the automation library implementation
    """

    def __init__(
        self, page_id: str, context_id: str, driver: "BrowserDriver", page_ref: Any
    ):
        self.id = page_id
        self.context_id = context_id
        self.driver = driver
        self.page_ref = page_ref

    async def goto(
        self, url: str, options: Optional["NavigationOptions"] = None
    ) -> Result[None, Exception]:
        """Navigate to a URL in this page"""
        try:
            return await self.driver.goto(self.id, url, options)
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return Error(e)

    async def current_url(self) -> Result[str, Exception]:
        """Get the current URL of the page"""
        return await self.driver.current_url(self.id)

    async def reload(self) -> Result[None, Exception]:
        """Reload the current page"""
        return await self.driver.reload(self.id)

    async def go_back(self) -> Result[None, Exception]:
        """Navigate to the previous page in history"""
        return await self.driver.go_back(self.id)

    async def go_forward(self) -> Result[None, Exception]:
        """Navigate to the next page in history"""
        return await self.driver.go_forward(self.id)

    async def close(self) -> Result[None, Exception]:
        """Close this page"""
        try:
            return await self.driver.close_page(self.id)
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)

    async def query_selector(self, selector: str) -> Result["ElementHandle", Exception]:
        result = await self.driver.query_selector(self.id, selector)
        if result.is_error():
            return Error(result.error)
        value = result.default_value(None)
        if value is None:
            return Error(Exception("No value returned from query_selector"))
        return Ok(value)

    async def query_selector_all(
        self, selector: str
    ) -> Result[List["ElementHandle"], Exception]:
        result = await self.driver.query_selector_all(self.id, selector)
        if result.is_error():
            return Error(result.error)
        values = result.default_value([])
        if values is None:
            return Error(Exception("No values returned from query_selector_all"))
        return Ok(values)

    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        return await self.driver.execute_script(self.id, script, *args)

    async def wait_for_selector(
        self, selector: str, options: Optional["WaitOptions"] = None
    ) -> Result["ElementHandle", Exception]:
        result = await self.driver.wait_for_selector(self.id, selector, options)
        if result.is_error():
            return Error(result.error)
        value = result.default_value(None)
        if value is None:
            return Error(Exception("No value returned from wait_for_selector"))
        return Ok(value)

    async def wait_for_navigation(
        self, options: Optional["NavigationOptions"] = None
    ) -> Result[None, Exception]:
        return await self.driver.wait_for_navigation(self.id, options)

    async def screenshot(
        self, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        return await self.driver.screenshot(self.id, path)

    async def get_page_source(self) -> Result[str, Exception]:
        """Get the HTML source of the page"""
        return await self.driver.get_source(self.id)

    async def click(
        self, selector: str, options: Optional["MouseOptions"] = None
    ) -> Result[None, Exception]:
        return await self.driver.click(self.id, selector, options)

    async def fill(
        self, selector: str, value: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        return await self.driver.fill(self.id, selector, value, options)

    async def double_click(
        self, selector: str, options: Optional["MouseOptions"] = None
    ) -> Result[None, Exception]:
        """Double click on an element"""
        return await self.driver.double_click(self.id, selector, options)

    async def type(
        self, selector: str, text: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        """Type text into an element"""
        return await self.driver.type(self.id, selector, text, options)

    async def select(
        self, selector: str, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        """Select an option in a dropdown"""
        return await self.driver.select(self.id, selector, value, text)


class BrowserContext:
    """
    Represents a browser context with its own session state
    (cookies, localStorage, etc.)
    """

    def __init__(
        self,
        context_id: str,
        driver: "BrowserDriver",
        manager: "BrowserManager",
        options: Optional[Dict[str, Any]] = None,
        context_ref: Optional[Any] = None,
        nickname: Optional[str] = None,
    ):
        self.id = context_id
        self.driver = driver
        self.manager = manager
        self.options = options or {}
        self.context_ref = context_ref
        self.pages: Dict[str, BrowserPage] = {}
        self.default_page_id: Optional[str] = None
        self.nickname = nickname or context_id 
    async def create_page(
        self, nickname: Optional[str] = None
    ) -> Result[BrowserPage, Exception]:
        """Create a new page in this context"""
        try:
            page_id = nickname or f"page-{len(self.pages) + 1}"

            if page_id in self.pages:
                return Error(Exception(f"Page with ID '{page_id}' already exists"))

            page_result = await self.driver.create_page(self.id)
            if page_result.is_error():
                return Error(page_result.error)

            page_ref = page_result.default_value(None)
            if page_ref is None:
                return Error(Exception("Failed to create page"))

            page = BrowserPage(
                page_id=page_id,
                context_id=self.id,
                driver=self.driver,
                page_ref=page_ref,
            )

            self.pages[page_id] = page

            if self.default_page_id is None:
                self.default_page_id = page_id

            return Ok(page)
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return Error(e)

    def get_page(self, page_id: Optional[str] = None) -> Result[BrowserPage, Exception]:
        """Get a page by ID or the default page"""
        try:
            page_id = page_id or self.default_page_id

            if page_id is None:
                return Error(Exception("No pages available in this context"))

            page = self.pages.get(page_id)
            if page is None:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            return Ok(page)
        except Exception as e:
            logger.error(f"Error getting page: {e}")
            return Error(e)

    async def close_page(self, page_id: Optional[str] = None) -> Result[None, Exception]:
        """Close a page by ID or the default page"""
        try:
            page_id = page_id or self.default_page_id
            
            if page_id is None:
                return Error(Exception("No pages available in this context"))

            page = self.pages.get(page_id)
            if page is None:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            return await page.close()
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)

    # Context-level input methods
    async def mouse_move(
        self, x: int, y: int, options: Optional["MouseOptions"] = None
    ) -> Result[None, Exception]:
        """Move the mouse to coordinates"""
        return await self.driver.mouse_move(self.id, x, y, options)

    async def mouse_down(
        self,
        button: "MouseButtonLiteral" = "left",
        options: Optional["MouseOptions"] = None,
    ) -> Result[None, Exception]:
        """Press a mouse button"""
        return await self.driver.mouse_down(self.id, button, options)

    async def mouse_up(
        self,
        button: "MouseButtonLiteral" = "left",
        options: Optional["MouseOptions"] = None,
    ) -> Result[None, Exception]:
        """Release a mouse button"""
        return await self.driver.mouse_up(self.id, button, options)

    async def mouse_click(
        self,
        button: "MouseButtonLiteral" = "left",
        options: Optional["MouseOptions"] = None,
    ) -> Result[None, Exception]:
        """Click at the current mouse position"""
        return await self.driver.mouse_click(self.id, button, options)

    async def mouse_double_click(
        self, x: int, y: int, options: Optional["MouseOptions"] = None
    ) -> Result[None, Exception]:
        """Double click at the specified coordinates"""
        return await self.driver.mouse_double_click(self.id, x, y, options)

    async def mouse_drag(
        self,
        source: 'CoordinateType',
        target: 'CoordinateType',
        options: Optional["DragOptions"] = None,
    ) -> Result[None, Exception]:
        """Drag from one element or position to another"""
        return await self.driver.mouse_drag(self.id, source, target, options)

    async def key_press(
        self, key: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        """Press a key or key combination"""
        return await self.driver.key_press(self.id, key, options)

    async def key_down(
        self, key: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        """Press and hold a key"""
        return await self.driver.key_down(self.id, key, options)

    async def key_up(
        self, key: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        """Release a key"""
        return await self.driver.key_up(self.id, key, options)

    async def close(self) -> Result[None, Exception]:
        """Close the context and all associated pages"""
        try:
            close_results = []
            for page in list(self.pages.values()):
                close_results.append(await page.close())

            self.pages.clear()
            self.default_page_id = None

            return await self.driver.close_context(self.id)
        except Exception as e:
            logger.error(f"Error closing context: {e}")
            return Error(e)
