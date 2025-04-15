import logging
import asyncio
import random
from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Type, Union

from expression import Result, Error

from silk.browsers.element import ElementHandle
from silk.browsers.types import (
    BrowserOptions,
    CoordinateType,
    DragOptions,
    MouseButtonLiteral,
    MouseOptions,
    NavigationOptions,
    TypeOptions,
    WaitOptions,
)

logger = logging.getLogger(__name__)


class BrowserDriver(Protocol):
    """
    Abstract browser driver interface that defines the contract for browser automation.

    All concrete browser implementations (like Playwright, Selenium, etc.) must
    implement this interface to be usable with the Silk action system.
    """

    options: BrowserOptions

    def __init__(self, options: BrowserOptions):
        """
        Initialize the browser driver with options

        Args:
            options: Configuration options for the browser
        """
        self.options = options

    async def __aenter__(self) -> "BrowserDriver":
        """Support for async context manager"""
        result = await self.launch()
        if result.is_error():
            raise result.error
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Cleanup when exiting the context manager"""
        await self.close()

    @abstractmethod
    async def launch(self) -> Result[None, Exception]:
        """
        Launch the browser

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def close(self) -> Result[None, Exception]:
        """
        Close the browser

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def create_context(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Result[str, Exception]:
        """
        Create a new browser context with isolated storage and return its ID

        Args:
            options: Optional context creation options

        Returns:
            Result containing the context ID or an error
        """
        pass

    @abstractmethod
    async def close_context(self, context_id: str) -> Result[None, Exception]:
        """
        Close a browser context

        Args:
            context_id: ID of the context to close

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def create_page(self, context_id: str) -> Result[str, Exception]:
        """
        Create a new page in the specified context

        Args:
            context_id: ID of the context to create the page in

        Returns:
            Result containing the page ID or an error
        """
        pass

    @abstractmethod
    async def close_page(self, page_id: str) -> Result[None, Exception]:
        """
        Close a page

        Args:
            page_id: ID of the page to close

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """
        Navigate a page to a URL

        Args:
            page_id: ID of the page to navigate
            url: The URL to navigate to
            options: Optional navigation options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def current_url(self, page_id: str) -> Result[str, Exception]:
        """
        Get the current URL of a page

        Args:
            page_id: ID of the page to get URL from

        Returns:
            Result containing the current URL or an error
        """
        pass

    @abstractmethod
    async def get_source(self, page_id: str) -> Result[str, Exception]:
        """
        Get the current page HTML source

        Args:
            page_id: ID of the page to get source from

        Returns:
            Result containing the HTML source or an error
        """
        pass

    @abstractmethod
    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        """
        Take a screenshot of a page and save it to the specified path

        Args:
            page_id: ID of the page to screenshot
            path: Optional path to save the screenshot

        Returns:
            Result with the screenshot path or image buffer, or an error
        """
        pass

    @abstractmethod
    async def reload(self, page_id: str) -> Result[None, Exception]:
        """
        Reload the current page

        Args:
            page_id: ID of the page to reload

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def go_back(self, page_id: str) -> Result[None, Exception]:
        """
        Go back to the previous page

        Args:
            page_id: ID of the page to go back to

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def go_forward(self, page_id: str) -> Result[None, Exception]:
        """
        Go forward to the next page

        Args:
            page_id: ID of the page to go forward to

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """
        Query a single element with the provided selector in a page

        Args:
            page_id: ID of the page to query
            selector: CSS or XPath selector

        Returns:
            Result containing the element handle or None if not found
        """
        pass

    @abstractmethod
    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        """
        Query all elements that match the provided selector in a page

        Args:
            page_id: ID of the page to query
            selector: CSS or XPath selector

        Returns:
            Result containing a list of element handles or an error
        """
        pass

    @abstractmethod
    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        """
        Wait for an element matching the selector to appear in a page

        Args:
            page_id: ID of the page to wait on
            selector: CSS or XPath selector
            options: Wait options including timeout, state, and poll interval

        Returns:
            Result containing the element handle or None if not found
        """
        pass

    @abstractmethod
    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """
        Wait for navigation to complete in a page

        Args:
            page_id: ID of the page to wait on
            options: Navigation options including timeout and wait condition

        Returns:
            Result indicating success or failure
        """
        pass

    # TODO the following interaction methods should be merged, they should work at both a context level and a page level
    # users should be able to easily click on an element or position within a context and trigger a mouse event at the same time
    @abstractmethod
    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """
        Click an element in a page

        Args:
            page_id: ID of the page containing the element
            selector: CSS or XPath selector
            options: Click options (button, count, delay, etc.)

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def double_click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """
        Double click an element in a page

        Args:
            page_id: ID of the page containing the element
            selector: CSS or XPath selector
            options: Click options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def type(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """
        Type text into an element

        Args:
            page_id: ID of the page for typing
            selector: CSS or XPath selector
            text: Text to type
            options: Typing options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """
        Fill an input element with text

        Args:
            page_id: ID of the page for filling
            selector: CSS or XPath selector
            text: Text to fill
            options: Fill options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        """
        Select an option in a <select> element

        Args:
            page_id: ID of the page for selection
            selector: CSS or XPath selector
            value: Option value to select
            text: Option text to select

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        """
        Execute JavaScript in the page context

        Args:
            page_id: ID of the page to execute script on
            script: JavaScript code to execute
            args: Arguments to pass to the script

        Returns:
            Result containing the script result or an error
        """
        pass

    @abstractmethod
    async def mouse_move(
        self,
        page_id: str,
        x: float,
        y: float,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """
        Move the mouse to the specified coordinates within a context

        Args:
            context_id: ID of the context for mouse movement
            x: X coordinate
            y: Y coordinate
            options: Mouse movement options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def mouse_down(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """
        Press a mouse button within a context

        Args:
            context_id: ID of the context for mouse action
            button: Mouse button to press
            options: Mouse options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def mouse_up(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """
        Release a mouse button within a context

        Args:
            page_id: ID of the page for mouse action
            button: Mouse button to release
            options: Mouse options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def mouse_click(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """
        Click at the current mouse position within a context

        Args:
            page_id: ID of the page for mouse action
            button: Mouse button to click with
            options: Mouse options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def mouse_double_click(
        self,
        page_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """
        Double click at the specified coordinates within a context

        Args:
            page_id: ID of the page for mouse action
            x: X coordinate
            y: Y coordinate
            options: Mouse options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def mouse_drag(
        self,
        page_id: str,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """
        Drag from one element or position to another within a context

        Args:
            page_id: ID of the page for drag operation
            source: Source coordinates
            target: Target coordinates
            options: Drag options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def key_press(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """
        Press a key or key combination within a context

        Args:
            page_id: ID of the page for keyboard action
            key: Key to press
            options: Key press options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def key_down(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """
        Press and hold a key within a context

        Args:
            page_id: ID of the page for keyboard action
            key: Key to press
            options: Key press options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def key_up(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """
        Release a key within a context

        Args:
            page_id: ID of the page for keyboard action
            key: Key to release
            options: Key press options

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def get_element_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """
        Get the text content of an element

        Args:
            page_id: ID of the page containing the element
            element: Element to get text from

        Returns:
            Result containing the text content or an error
        """
        pass

    @abstractmethod
    async def get_element_attribute(
        self, page_id: str, element: ElementHandle, name: str
    ) -> Result[Optional[str], Exception]:
        """
        Get an attribute value from an element

        Args:
            page_id: ID of the page containing the element
            element: Element to get attribute from
            name: Name of the attribute

        Returns:
            Result containing the attribute value or an error
        """
        pass

    @abstractmethod
    async def get_element_bounding_box(
        self, page_id: str, element: ElementHandle
    ) -> Result[Dict[str, float], Exception]:
        """
        Get the bounding box of an element

        Args:
            page_id: ID of the page containing the element
            element: Element to get bounding box from

        Returns:
            Result containing the bounding box or an error
        """
        pass

    @abstractmethod
    async def click_element(
        self, page_id: str, element: ElementHandle
    ) -> Result[None, Exception]:
        """
        Click an element

        Args:
            page_id: ID of the page containing the element
            element: Element to click

        Returns:
            Result indicating success or failure
        """
        pass

    @abstractmethod
    async def get_element_html(
        self, page_id: str, element: ElementHandle, outer: bool = True
    ) -> Result[str, Exception]:
        """
        Get the HTML content of an element

        Args:
            page_id: ID of the page containing the element
            element: Element to get HTML from
            outer: Whether to include the element's outer HTML (True) or just inner HTML (False)

        Returns:
            Result containing the HTML content or an error
        """
        pass

    @abstractmethod
    async def get_element_inner_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """
        Get the innerText of an element (visible text only)

        Args:
            page_id: ID of the page containing the element
            element: Element to get innerText from

        Returns:
            Result containing the innerText or an error
        """
        pass

    @abstractmethod
    async def extract_table(
        self,
        page_id: str,
        table_element: ElementHandle,
        include_headers: bool = True,
        header_selector: str = "th",
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> Result[List[Dict[str, str]], Exception]:
        """
        Extract data from an HTML table element

        Args:
            page_id: ID of the page containing the table
            table_element: Element handle for the table
            include_headers: Whether to use table headers as keys
            header_selector: Selector for header cells
            row_selector: Selector for row elements
            cell_selector: Selector for cell elements

        Returns:
            Result containing table data as list of dictionaries
        """
        pass

    @abstractmethod
    async def scroll(
        self,
        page_id: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Result[None, Exception]:
        """
        Scroll the page to specific coordinates or scroll an element into view

        Args:
            page_id: ID of the page to scroll
            x: Optional X coordinate to scroll to
            y: Optional Y coordinate to scroll to
            selector: Optional CSS selector of element to scroll into view
            options: Optional scroll behavior options

        Returns:
            Result indicating success or failure
        """
        pass

    async def execute_cdp_cmd(
        self, page_id: str, cmd: str, *args: Any
    ) -> Result[Any, Exception]:
        """
        Execute a CDP command
        """
        # Default implementation returns Error since not all drivers support CDP
        return Error(Exception("CDP commands not supported by this driver"))
