"""
Tests for the Playwright implementation of the browser driver in Silk.
"""

import os
import pytest
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, AsyncMock

from expression.core import Ok, Error

from silk.browsers.driver import BrowserDriver
from silk.browsers.element import ElementHandle
from silk.browsers.drivers.playwright import PlaywrightDriver, PlaywrightElementHandle
from silk.browsers.context import BrowserContext, BrowserPage
from silk.models.browser import (
    BrowserOptions,
    ClickOptions,
    NavigationOptions,
    TypeOptions,
    WaitOptions,
)


# Unit Tests - Using mocks to test functionality without actual browser
class TestPlaywrightDriverUnit:
    """Unit tests for PlaywrightDriver using mocks."""

    @pytest.mark.asyncio
    async def test_launch_browser(self, playwright_driver):
        """Test launching the browser."""
        with patch("playwright.async_api.async_playwright") as mock_playwright:
            # Setup mocks
            mock_playwright_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)

            # Replace the playwright and browser on the driver for this test
            playwright_driver.playwright = mock_playwright_instance
            playwright_driver.browser = mock_browser
            playwright_driver.initialized = True

            # Test the launch method
            result = await playwright_driver.launch()

            # Assertions
            assert result.is_ok()
            assert playwright_driver.playwright is mock_playwright_instance
            assert playwright_driver.browser is mock_browser
            assert playwright_driver.initialized is True
            mock_playwright_instance.chromium.launch.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_context(self, playwright_driver):
        """Test creating a browser context."""
        # Setup mocks
        mock_launch = AsyncMock(return_value=Ok(None))
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        # Configure the mock browser for this test
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        with patch.object(playwright_driver, "launch", mock_launch):
            with patch.object(playwright_driver, "browser", mock_browser):
                # Test create_context method
                result = await playwright_driver.create_context()

                # Assertions
                assert result.is_ok()
                context_id = result.default_value(None)
                assert context_id in playwright_driver.contexts
                assert playwright_driver.contexts[context_id] == mock_context
                mock_browser.new_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_page(self, playwright_driver):
        """Test creating a page in a context."""
        # Setup mocks
        context_id = "test-context"
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        playwright_driver.contexts[context_id] = mock_context

        # Test create_page method
        result = await playwright_driver.create_page(context_id)

        # Assertions
        assert result.is_ok()
        page_id = result.default_value(None)
        assert page_id in playwright_driver.pages
        assert playwright_driver.pages[page_id] == mock_page
        mock_context.new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_goto(self, playwright_driver):
        """Test navigating to a URL."""
        # Setup mocks
        page_id = "test-page"
        mock_page = AsyncMock()
        playwright_driver.pages[page_id] = mock_page
        url = "https://example.com"
        options = NavigationOptions(timeout=5000, wait_until="networkidle")

        # Mock the goto method to return a successful result
        mock_page.goto = AsyncMock(return_value=None)

        # Test goto method
        result = await playwright_driver.goto(page_id, url, options)

        # Assertions
        assert result.is_ok()
        mock_page.goto.assert_called_once_with(url, timeout=5000, wait_until="networkidle")

    @pytest.mark.asyncio
    async def test_query_selector(self, playwright_driver):
        """Test querying for an element."""
        # Setup mocks
        page_id = "test-page"
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        playwright_driver.pages[page_id] = mock_page
        mock_page.query_selector = AsyncMock(return_value=mock_element)
        selector = "#test-element"

        # Test query_selector method
        result = await playwright_driver.query_selector(page_id, selector)

        # Assertions
        assert result.is_ok()
        element = result.default_value(None)
        assert isinstance(element, PlaywrightElementHandle)
        assert element.element_ref == mock_element
        assert element.page_id == page_id
        assert element.selector == selector
        mock_page.query_selector.assert_called_once_with(selector)

    @pytest.mark.asyncio
    async def test_click(self, playwright_driver):
        """Test clicking an element."""
        # Setup mocks
        page_id = "test-page"
        mock_page = AsyncMock()
        playwright_driver.pages[page_id] = mock_page
        selector = "#test-button"
        options = ClickOptions(timeout=3000, button="left")

        # Mock the click method to return a successful result
        mock_page.click = AsyncMock(return_value=None)

        # Test click method
        result = await playwright_driver.click(page_id, selector, options)

        # Assertions
        assert result.is_ok()
        mock_page.click.assert_called_once_with(
            selector, timeout=3000, button="left"
        )

    @pytest.mark.asyncio
    async def test_fill(self, playwright_driver):
        """Test filling a form element."""
        # Setup mocks
        page_id = "test-page"
        mock_page = AsyncMock()
        playwright_driver.pages[page_id] = mock_page
        selector = "#test-input"
        text = "test input text"
        options = TypeOptions(timeout=3000)

        # Mock the fill method to return a successful result
        mock_page.fill = AsyncMock(return_value=None)

        # Test fill method
        result = await playwright_driver.fill(page_id, selector, text, options)

        # Assertions
        assert result.is_ok()
        mock_page.fill.assert_called_once_with(selector, text, timeout=3000)

    @pytest.mark.asyncio
    async def test_execute_script(self, playwright_driver):
        """Test executing JavaScript."""
        # Setup mocks
        page_id = "test-page"
        mock_page = AsyncMock()
        playwright_driver.pages[page_id] = mock_page
        script = "return document.title"
        
        # Mock the evaluate method to return a successful result
        mock_page.evaluate = AsyncMock(return_value="Test Page")

        # Test execute_script method
        result = await playwright_driver.execute_script(page_id, script)

        # Assertions
        assert result.is_ok()
        assert result.default_value(None) == "Test Page"
        mock_page.evaluate.assert_called_once_with(script)

    @pytest.mark.asyncio
    async def test_close(self, playwright_driver):
        """Test closing the browser."""
        # Setup mocks
        mock_context1 = AsyncMock()
        mock_context2 = AsyncMock()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        
        playwright_driver.contexts = {
            "context1": mock_context1,
            "context2": mock_context2
        }
        playwright_driver.browser = mock_browser
        playwright_driver.playwright = mock_playwright
        playwright_driver.initialized = True

        # Mock the close methods to return a successful result
        mock_context1.close = AsyncMock(return_value=None)
        mock_context2.close = AsyncMock(return_value=None)
        mock_browser.close = AsyncMock(return_value=None)
        mock_playwright.stop = AsyncMock(return_value=None)

        # Test close method
        result = await playwright_driver.close()

        # Assertions
        assert result.is_ok()
        assert not playwright_driver.initialized
        mock_context1.close.assert_called_once()
        mock_context2.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


class TestPlaywrightElementHandleUnit:
    """Unit tests for PlaywrightElementHandle using mocks."""

    @pytest.mark.asyncio
    async def test_get_text(self, element_handle):
        """Test getting text content from an element."""
        # Setup mock
        element_handle.element_ref.text_content = AsyncMock(return_value="Test Text")

        # Test get_text method
        result = await element_handle.get_text()

        # Assertions
        assert result.is_ok()
        assert result.default_value(None) == "Test Text"
        element_handle.element_ref.text_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_attribute(self, element_handle):
        """Test getting an attribute from an element."""
        # Setup mock
        element_handle.element_ref.get_attribute = AsyncMock(return_value="attribute-value")

        # Test get_attribute method
        result = await element_handle.get_attribute("data-test")

        # Assertions
        assert result.is_ok()
        assert result.default_value(None) == "attribute-value"
        element_handle.element_ref.get_attribute.assert_called_once_with("data-test")

    @pytest.mark.asyncio
    async def test_click(self, element_handle):
        """Test clicking an element."""
        # Setup mock
        element_handle.element_ref.click = AsyncMock(return_value=None)
        
        # Test click method
        result = await element_handle.click()

        # Assertions
        assert result.is_ok()
        element_handle.element_ref.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill(self, element_handle):
        """Test filling an input element."""
        # Setup mock
        element_handle.element_ref.fill = AsyncMock(return_value=None)
        
        # Test fill method
        result = await element_handle.fill("test input")

        # Assertions
        assert result.is_ok()
        element_handle.element_ref.fill.assert_called_once_with("test input")

    @pytest.mark.asyncio
    async def test_is_visible(self, element_handle):
        """Test checking element visibility."""
        # Setup mock
        element_handle.element_ref.is_visible = AsyncMock(return_value=True)

        # Test is_visible method
        result = await element_handle.is_visible()

        # Assertions
        assert result.is_ok()
        assert result.default_value(None) is True
        element_handle.element_ref.is_visible.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_bounding_box(self, element_handle):
        """Test getting element bounding box."""
        # Setup mock
        element_handle.element_ref.bounding_box = AsyncMock(return_value={
            "x": 10, "y": 20, "width": 100, "height": 50
        })

        # Test get_bounding_box method
        result = await element_handle.get_bounding_box()

        # Assertions
        assert result.is_ok()
        box = result.default_value(None)
        assert box["x"] == 10
        assert box["y"] == 20
        assert box["width"] == 100
        assert box["height"] == 50
        element_handle.element_ref.bounding_box.assert_called_once()