import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, List

from silk.browser.driver import BrowserOptions, BrowserDriver, ElementHandle


class TestBrowserOptions:
    def test_browser_options_defaults(self):
        options = BrowserOptions()
        
        assert options.headless is True
        assert options.timeout == 30000
        assert options.viewport_width == 1366
        assert options.viewport_height == 768
        assert options.proxy is None
        assert options.extra_args == {}
    
    def test_browser_options_custom(self):
        options = BrowserOptions(
            headless=False,
            timeout=60000,
            viewport_width=1920,
            viewport_height=1080,
            proxy="http://proxy:8080",
            extra_args={"disable-gpu": True}
        )
        
        assert options.headless is False
        assert options.timeout == 60000
        assert options.viewport_width == 1920
        assert options.viewport_height == 1080
        assert options.proxy == "http://proxy:8080"
        assert options.extra_args == {"disable-gpu": True}


class MockElementHandle(ElementHandle):
    """Concrete implementation of ElementHandle for testing"""
    
    async def click(self) -> None:
        pass
    
    async def type(self, text: str) -> None:
        pass
    
    async def get_text(self) -> str:
        return "Mock Element Text"
    
    async def get_attribute(self, name: str) -> Optional[str]:
        return f"mock-{name}"
    
    async def is_visible(self) -> bool:
        return True


class MockBrowserDriver(BrowserDriver[MockElementHandle]):
    """Concrete implementation of BrowserDriver for testing"""
    
    def __init__(self, options: BrowserOptions):
        super().__init__(options)
        self._current_url = ""
    
    async def launch(self) -> None:
        pass
    
    async def close(self) -> None:
        pass
    
    async def goto(self, url: str) -> None:
        self._current_url = url
    
    async def current_url(self) -> str:
        return self._current_url
    
    async def get_page_source(self) -> str:
        return "<html><body>Mock page</body></html>"
    
    async def take_screenshot(self, path: Path) -> None:
        pass
    
    async def query_selector(self, selector: str) -> Optional[MockElementHandle]:
        return MockElementHandle()
    
    async def query_selector_all(self, selector: str) -> List[MockElementHandle]:
        return [MockElementHandle(), MockElementHandle()]
    
    async def execute_script(self, script: str, *args) -> str:
        return "Executed script"
    
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Optional[MockElementHandle]:
        return MockElementHandle()
    
    async def wait_for_navigation(self, timeout: Optional[int] = None) -> None:
        pass


class TestBrowserDriver:
    @pytest.mark.asyncio
    async def test_browser_driver_goto(self):
        options = BrowserOptions()
        driver = MockBrowserDriver(options)
        
        await driver.goto("https://example.com")
        
        current_url = await driver.current_url()
        assert current_url == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_browser_driver_query_selector(self):
        options = BrowserOptions()
        driver = MockBrowserDriver(options)
        
        element = await driver.query_selector(".test-selector")
        
        assert element is not None
        assert isinstance(element, MockElementHandle)
        
        text = await element.get_text()
        assert text == "Mock Element Text"
    
    @pytest.mark.asyncio
    async def test_browser_driver_query_selector_all(self):
        options = BrowserOptions()
        driver = MockBrowserDriver(options)
        
        elements = await driver.query_selector_all(".test-selector")
        
        assert len(elements) == 2
        assert all(isinstance(element, MockElementHandle) for element in elements)
    
    def test_browser_driver_pipe(self):
        options = BrowserOptions()
        driver = MockBrowserDriver(options)
        
        def processor(browser: BrowserDriver):
            return "Processed"
        
        result = driver.pipe(processor)
        assert result == "Processed" 