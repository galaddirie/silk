import asyncio
import pytest
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

from silk.browsers.driver import BrowserDriver
from silk.selectors.selector import Selector, SelectorGroup


@pytest.fixture
def mock_driver() -> AsyncMock:
    """Provides a mock Driver implementation for testing."""
    driver = AsyncMock(spec=BrowserDriver)
    
    # Mock common browser methods
    driver.goto = AsyncMock(return_value=None)
    driver.get_by_selector = AsyncMock(return_value=MagicMock())
    driver.get_text = AsyncMock(return_value="Sample Text")
    driver.get_attribute = AsyncMock(return_value="sample-attribute")
    driver.click = AsyncMock(return_value=None)
    
    # Mouse action methods
    driver.mouse_down = AsyncMock(return_value=None)
    driver.mouse_up = AsyncMock(return_value=None)
    driver.mouse_move = AsyncMock(return_value=None)
    driver.mouse_move_to_element = AsyncMock(return_value=None)
    driver.mouse_click = AsyncMock(return_value=None)
    driver.double_click = AsyncMock(return_value=None)
    driver.click_with_options = AsyncMock(return_value=None)
    driver.drag = AsyncMock(return_value=None)
    
    # Keyboard action methods
    driver.key_down = AsyncMock(return_value=None)
    driver.key_up = AsyncMock(return_value=None)
    driver.press = AsyncMock(return_value=None)
    driver.fill = AsyncMock(return_value=None)
    
    # Element handling
    driver.query_selector = AsyncMock(return_value=MagicMock())
    
    return driver


@pytest.fixture
def mock_selector() -> MagicMock:
    """Provides a mock Selector implementation for testing."""
    selector = MagicMock(spec=Selector)
    selector.selector_string = ".sample-selector"
    selector.selector_type = "css"
    
    return selector


@pytest.fixture
def mock_selector_group() -> MagicMock:
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
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close() 