"""
Tests for the BrowserDriver abstract class.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pytest
from expression import Error, Ok, Result

from silk.browsers.driver import BrowserDriver
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


class MockBrowserDriver(BrowserDriver):
    """A concrete implementation of BrowserDriver for testing."""

    def __init__(self, options: BrowserOptions):
        super().__init__(options)
        self.launched = False
        self.closed = False
        self.contexts = {}
        self.pages = {}

    async def launch(self) -> Result[None, Exception]:
        self.launched = True
        return Ok(None)

    async def close(self) -> Result[None, Exception]:
        self.closed = True
        return Ok(None)

    async def create_context(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Result[str, Exception]:
        context_id = f"context-{len(self.contexts)}"
        self.contexts[context_id] = options or {}
        return Ok(context_id)

    async def close_context(self, context_id: str) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        del self.contexts[context_id]
        return Ok(None)

    async def create_page(self, context_id: str) -> Result[str, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        page_id = f"page-{len(self.pages)}"
        self.pages[page_id] = {"context_id": context_id}
        return Ok(page_id)

    async def close_page(self, page_id: str) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        del self.pages[page_id]
        return Ok(None)

    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def current_url(self, page_id: str) -> Result[str, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("https://example.com")

    async def get_source(self, page_id: str) -> Result[str, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("<html><body>Test</body></html>")

    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(Path("test.png") if path else b"mock_screenshot_data")

    async def reload(self, page_id: str) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def go_back(self, page_id: str) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def go_forward(self, page_id: str) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok([])

    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def double_click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def type(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def mouse_move(
        self,
        context_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def mouse_down(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def mouse_up(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def mouse_click(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def mouse_double_click(
        self,
        context_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def mouse_drag(
        self,
        context_id: str,
        source: Union[str, ElementHandle, CoordinateType],
        target: Union[str, ElementHandle, CoordinateType],
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def key_press(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def key_down(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def key_up(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        if context_id not in self.contexts:
            return Error(Exception(f"Context {context_id} not found"))
        return Ok(None)

    async def get_element_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("Test Text")

    async def get_element_attribute(
        self, page_id: str, element: ElementHandle, name: str
    ) -> Result[Optional[str], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("test-attribute")

    async def get_element_bounding_box(
        self, page_id: str, element: ElementHandle
    ) -> Result[Dict[str, float], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok({"x": 0, "y": 0, "width": 100, "height": 100})

    async def click_element(
        self, page_id: str, element: ElementHandle
    ) -> Result[None, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok(None)

    async def get_element_html(
        self, page_id: str, element: ElementHandle, outer: bool = True
    ) -> Result[str, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("<div>Test</div>")

    async def get_element_inner_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok("Test Inner Text")

    async def extract_table(
        self,
        page_id: str,
        table_element: ElementHandle,
        include_headers: bool = True,
        header_selector: str = "th",
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> Result[List[Dict[str, str]], Exception]:
        if page_id not in self.pages:
            return Error(Exception(f"Page {page_id} not found"))
        return Ok([{"header1": "value1", "header2": "value2"}])


class TestBrowserDriver:
    """Test suite for the BrowserDriver abstract class."""

    @pytest.fixture
    def driver(self, browser_options):
        """Create a test instance of MockBrowserDriver."""
        return MockBrowserDriver(browser_options)

    @pytest.mark.asyncio
    async def test_launch_and_close(self, driver):
        """Test launching and closing the browser."""
        # Launch browser
        result = await driver.launch()
        assert result.is_ok()
        assert driver.launched
        assert not driver.closed

        # Close browser
        result = await driver.close()
        assert result.is_ok()
        assert driver.closed

    @pytest.mark.asyncio
    async def test_context_management(self, driver):
        """Test creating and closing browser contexts."""
        # Launch browser first
        await driver.launch()

        # Create context
        result = await driver.create_context()
        assert result.is_ok()
        context_id = result.default_value(None)
        assert context_id in driver.contexts

        # Create page in context
        result = await driver.create_page(context_id)
        assert result.is_ok()
        page_id = result.default_value(None)
        assert page_id in driver.pages
        assert driver.pages[page_id]["context_id"] == context_id

        # Close page
        result = await driver.close_page(page_id)
        assert result.is_ok()
        assert page_id not in driver.pages

        # Close context
        result = await driver.close_context(context_id)
        assert result.is_ok()
        assert context_id not in driver.contexts

    @pytest.mark.asyncio
    async def test_navigation(self, driver):
        """Test page navigation methods."""
        # Launch browser and create context/page
        await driver.launch()
        context_result = await driver.create_context()
        context_id = context_result.default_value(None)
        page_result = await driver.create_page(context_id)
        page_id = page_result.default_value(None)

        # Test navigation methods
        result = await driver.goto(page_id, "https://example.com")
        assert result.is_ok()

        result = await driver.current_url(page_id)
        assert result.is_ok()
        assert result.default_value(None) == "https://example.com"

        result = await driver.reload(page_id)
        assert result.is_ok()

        result = await driver.go_back(page_id)
        assert result.is_ok()

        result = await driver.go_forward(page_id)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_element_interaction(self, driver, mock_element_handle):
        """Test element interaction methods."""
        # Launch browser and create context/page
        await driver.launch()
        context_result = await driver.create_context()
        context_id = context_result.default_value(None)
        page_result = await driver.create_page(context_id)
        page_id = page_result.default_value(None)

        # Test element methods
        result = await driver.get_element_text(page_id, mock_element_handle)
        assert result.is_ok()
        assert result.default_value(None) == "Test Text"

        result = await driver.get_element_attribute(
            page_id, mock_element_handle, "test"
        )
        assert result.is_ok()
        assert result.default_value(None) == "test-attribute"

        result = await driver.get_element_bounding_box(page_id, mock_element_handle)
        assert result.is_ok()
        box = result.default_value(None)
        assert box["x"] == 0
        assert box["y"] == 0
        assert box["width"] == 100
        assert box["height"] == 100

        result = await driver.click_element(page_id, mock_element_handle)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_error_handling(self, driver):
        """Test error handling for invalid page/context IDs."""
        # Launch browser first
        await driver.launch()

        # Test with invalid page ID
        result = await driver.goto("invalid-page", "https://example.com")
        assert result.is_error()
        assert "Page invalid-page not found" in str(result.error)

        # Test with invalid context ID
        result = await driver.create_page("invalid-context")
        assert result.is_error()
        assert "Context invalid-context not found" in str(result.error)

    @pytest.mark.asyncio
    async def test_mouse_and_keyboard(self, driver):
        """Test mouse and keyboard interaction methods."""
        # Launch browser and create context
        await driver.launch()
        context_result = await driver.create_context()
        context_id = context_result.default_value(None)

        # Test mouse methods
        result = await driver.mouse_move(context_id, 100, 100)
        assert result.is_ok()

        result = await driver.mouse_down(context_id)
        assert result.is_ok()

        result = await driver.mouse_up(context_id)
        assert result.is_ok()

        result = await driver.mouse_click(context_id)
        assert result.is_ok()

        result = await driver.mouse_double_click(context_id, 100, 100)
        assert result.is_ok()

        # Test keyboard methods
        result = await driver.key_press(context_id, "Enter")
        assert result.is_ok()

        result = await driver.key_down(context_id, "Shift")
        assert result.is_ok()

        result = await driver.key_up(context_id, "Shift")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_screenshot(self, driver):
        """Test taking screenshots."""
        # Launch browser and create context/page
        await driver.launch()
        context_result = await driver.create_context()
        context_id = context_result.default_value(None)
        page_result = await driver.create_page(context_id)
        page_id = page_result.default_value(None)

        # Test screenshot with path
        result = await driver.screenshot(page_id, Path("test.png"))
        assert result.is_ok()
        assert isinstance(result.default_value(None), Path)
        assert result.default_value(None).name == "test.png"

        # Test screenshot without path
        result = await driver.screenshot(page_id)
        assert result.is_ok()
        assert isinstance(result.default_value(None), bytes)
        assert result.default_value(None) == b"mock_screenshot_data"
