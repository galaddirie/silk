import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from silk.browser.driver import BrowserDriver
from silk.selectors.selector import Selector, SelectorGroup


@pytest.fixture
def mock_driver():
    """Provides a mock Driver implementation for testing."""
    driver = AsyncMock(spec=BrowserDriver)
    
    # Mock common browser methods
    driver.goto = AsyncMock(return_value=None)
    driver.get_by_selector = AsyncMock(return_value=MagicMock())
    driver.get_text = AsyncMock(return_value="Sample Text")
    driver.get_attribute = AsyncMock(return_value="sample-attribute")
    driver.click = AsyncMock(return_value=None)
    driver.fill = AsyncMock(return_value=None)
    
    return driver


@pytest.fixture
def mock_selector():
    """Provides a mock Selector implementation for testing."""
    selector = MagicMock(spec=Selector)
    selector.selector_string = ".sample-selector"
    selector.selector_type = "css"
    
    return selector


@pytest.fixture
def mock_selector_group():
    """Provides a mock SelectorGroup implementation for testing."""
    selector1 = MagicMock(spec=Selector)
    selector1.selector_string = ".primary-selector"
    selector1.selector_type = "css"
    
    selector2 = MagicMock(spec=Selector)
    selector2.selector_string = ".fallback-selector"
    selector2.selector_type = "css"
    
    selector_group = MagicMock(spec=SelectorGroup)
    selector_group.name = "test_group"
    selector_group.selectors = [selector1, selector2]
    
    return selector_group


@pytest.fixture
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close() 