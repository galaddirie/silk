"""
Pytest fixtures for the Silk browser automation framework.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from expression.core import Error, Ok

from silk.actions.context import ActionContext
from silk.browsers.context import BrowserContext, BrowserPage
from silk.browsers.driver import BrowserDriver
from silk.browsers.drivers.playwright import PlaywrightDriver, PlaywrightElementHandle
from silk.browsers.element import ElementHandle
from silk.browsers.manager import BrowserManager
from silk.browsers.types import BrowserOptions
from silk.selectors.selector import Selector, SelectorGroup


# Helper functions to create awaitable results
async def async_ok(value):
    """Create an awaitable Ok result."""
    return Ok(value)


async def async_error(error):
    """Create an awaitable Error result."""
    return Error(error)


# Enable async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_element_handle() -> MagicMock:
    """Fixture to create a mock ElementHandle."""
    mock = MagicMock(spec=ElementHandle)

    # Mock async methods with awaitable results
    mock.get_text = AsyncMock(return_value=Ok("Mock Text"))
    mock.get_inner_text = AsyncMock(return_value=Ok("Mock Inner Text"))
    mock.get_html = AsyncMock(return_value=Ok("<div>Mock HTML</div>"))
    mock.get_attribute = AsyncMock(return_value=Ok("mock-attribute"))
    mock.get_property = AsyncMock(return_value=Ok("mock-property"))
    mock.get_bounding_box = AsyncMock(
        return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50})
    )
    mock.click = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.is_visible = AsyncMock(return_value=Ok(True))
    mock.is_enabled = AsyncMock(return_value=Ok(True))
    mock.get_parent = AsyncMock(return_value=Ok(None))
    mock.get_children = AsyncMock(return_value=Ok([]))
    mock.query_selector = AsyncMock(return_value=Ok(None))
    mock.query_selector_all = AsyncMock(return_value=Ok([]))
    mock.scroll_into_view = AsyncMock(return_value=Ok(None))

    # Set up non-async methods
    mock.get_selector.return_value = "#mock-selector"
    mock.get_page_id.return_value = "mock-page-id"
    mock.selector = "#mock-selector"
    mock.page_id = "mock-page-id"

    return mock


@pytest.fixture
def mock_browser_driver() -> MagicMock:
    """Fixture to create a mock BrowserDriver."""
    mock = MagicMock(spec=BrowserDriver)

    # Mock async methods with awaitable Result returns
    mock.launch = AsyncMock(return_value=Ok(None))
    mock.close = AsyncMock(return_value=Ok(None))
    mock.create_context = AsyncMock(return_value=Ok("mock-context-id"))
    mock.close_context = AsyncMock(return_value=Ok(None))
    mock.create_page = AsyncMock(return_value=Ok("mock-page-ref"))
    mock.close_page = AsyncMock(return_value=Ok(None))
    mock.goto = AsyncMock(return_value=Ok(None))
    mock.current_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.get_source = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
    mock.screenshot = AsyncMock(return_value=Ok(Path("mock_screenshot.png")))
    mock.reload = AsyncMock(return_value=Ok(None))
    mock.go_back = AsyncMock(return_value=Ok(None))
    mock.go_forward = AsyncMock(return_value=Ok(None))
    mock.query_selector = AsyncMock(return_value=Ok(None))
    mock.query_selector_all = AsyncMock(return_value=Ok([]))
    mock.wait_for_selector = AsyncMock(return_value=Ok(None))
    mock.wait_for_navigation = AsyncMock(return_value=Ok(None))
    mock.click = AsyncMock(return_value=Ok(None))
    mock.double_click = AsyncMock(return_value=Ok(None))
    mock.type = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.execute_script = AsyncMock(return_value=Ok({"result": "mock-result"}))
    mock.mouse_move = AsyncMock(return_value=Ok(None))
    mock.mouse_down = AsyncMock(return_value=Ok(None))
    mock.mouse_up = AsyncMock(return_value=Ok(None))
    mock.mouse_click = AsyncMock(return_value=Ok(None))
    mock.mouse_double_click = AsyncMock(return_value=Ok(None))
    mock.mouse_drag = AsyncMock(return_value=Ok(None))
    mock.key_press = AsyncMock(return_value=Ok(None))
    mock.key_down = AsyncMock(return_value=Ok(None))
    mock.key_up = AsyncMock(return_value=Ok(None))
    mock.get_element_text = AsyncMock(return_value=Ok("Mock Element Text"))
    mock.get_element_attribute = AsyncMock(return_value=Ok("mock-element-attribute"))
    mock.get_element_bounding_box = AsyncMock(
        return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50})
    )
    mock.click_element = AsyncMock(return_value=Ok(None))
    mock.get_element_html = AsyncMock(return_value=Ok("<div>Mock Element HTML</div>"))
    mock.get_element_inner_text = AsyncMock(return_value=Ok("Mock Element Inner Text"))
    mock.extract_table = AsyncMock(
        return_value=Ok([{"header1": "value1", "header2": "value2"}])
    )

    return mock


@pytest.fixture
def browser_options() -> BrowserOptions:
    """Fixture to create browser options for testing."""
    return BrowserOptions(
        headless=True,
        timeout=5000,  # Short timeout for tests
        viewport_width=1280,
        viewport_height=720,
        stealth_mode=False,
    )


@pytest.fixture
def mock_browser_page(mock_browser_driver) -> MagicMock:
    """Fixture to create a mock BrowserPage."""
    mock = MagicMock(spec=BrowserPage)
    mock.id = "mock-page-id"
    mock.context_id = "mock-context-id"
    mock.driver = mock_browser_driver
    mock.page_ref = "mock-page-ref"

    # Mock the async methods with awaitable results
    mock.goto = AsyncMock(return_value=Ok(None))
    mock.current_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.reload = AsyncMock(return_value=Ok(None))
    mock.go_back = AsyncMock(return_value=Ok(None))
    mock.go_forward = AsyncMock(return_value=Ok(None))
    mock.close = AsyncMock(return_value=Ok(None))
    mock.query_selector = AsyncMock(return_value=Ok(None))
    mock.query_selector_all = AsyncMock(return_value=Ok([]))
    mock.execute_script = AsyncMock(return_value=Ok({"result": "mock-result"}))
    mock.wait_for_selector = AsyncMock(return_value=Ok(None))
    mock.wait_for_navigation = AsyncMock(return_value=Ok(None))
    mock.screenshot = AsyncMock(return_value=Ok(Path("mock_screenshot.png")))
    mock.get_page_source = AsyncMock(
        return_value=Ok("<html><body>Mock page</body></html>")
    )
    mock.click = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.double_click = AsyncMock(return_value=Ok(None))
    mock.type = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))

    return mock


@pytest.fixture
def mock_browser_context(mock_browser_driver, mock_browser_page) -> MagicMock:
    """Fixture to create a mock BrowserContext."""
    mock = MagicMock(spec=BrowserContext)
    mock.id = "mock-context-id"
    mock.driver = mock_browser_driver
    mock.options = {}
    mock.context_ref = "mock-context-ref"
    mock.pages = {"mock-page-id": mock_browser_page}
    mock.default_page_id = "mock-page-id"
    mock.nickname = "mock-context-id"

    # Mock the async methods with awaitable results
    mock.create_page = AsyncMock(return_value=Ok(mock_browser_page))
    mock.get_page.return_value = Ok(mock_browser_page)  # This one is not async
    mock.mouse_move = AsyncMock(return_value=Ok(None))
    mock.mouse_down = AsyncMock(return_value=Ok(None))
    mock.mouse_up = AsyncMock(return_value=Ok(None))
    mock.mouse_click = AsyncMock(return_value=Ok(None))
    mock.mouse_double_click = AsyncMock(return_value=Ok(None))
    mock.mouse_drag = AsyncMock(return_value=Ok(None))
    mock.key_press = AsyncMock(return_value=Ok(None))
    mock.key_down = AsyncMock(return_value=Ok(None))
    mock.key_up = AsyncMock(return_value=Ok(None))
    mock.close = AsyncMock(return_value=Ok(None))

    return mock


@pytest.fixture
def mock_browser_manager(mock_browser_driver, mock_browser_context) -> MagicMock:
    """Fixture to create a mock BrowserManager."""
    mock = MagicMock(spec=BrowserManager)
    mock.default_options = BrowserOptions()
    mock.drivers = {"mock-driver-id": mock_browser_driver}
    mock.contexts = {"mock-context-id": mock_browser_context}
    mock.default_context_id = "mock-context-id"

    # Mock the async methods with awaitable results
    mock.create_context = AsyncMock(return_value=Ok(mock_browser_context))
    mock.get_context.return_value = Ok(mock_browser_context)  # This one is not async
    mock.close_context = AsyncMock(return_value=Ok(None))
    mock.close_all = AsyncMock(return_value=Ok(None))

    return mock


class MockActionContext(ActionContext):
    """A subclass of ActionContext that allows mocking methods for testing."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mock_responses: Dict[str, Any] = {}
    
    async def get_page(self):
        """Mock implementation of get_page that can be configured in tests."""
        if "get_page" in self._mock_responses:
            return self._mock_responses["get_page"]
        return await super().get_page()
    
    async def get_driver(self):
        """Mock implementation of get_driver that can be configured in tests."""
        if "get_driver" in self._mock_responses:
            return self._mock_responses["get_driver"]
        return await super().get_driver()
    
    def set_mock_response(self, method_name: str, response: Any):
        """Configure a mock response for a method."""
        self._mock_responses[method_name] = response


@pytest.fixture
def action_context(mock_browser_manager, mock_browser_page, mock_browser_driver) -> MockActionContext:
    """Fixture to create a MockActionContext for testing."""
    context = MockActionContext(
        browser_manager=mock_browser_manager,
        context_id="mock-context-id",
        page_id="mock-page-id",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    # Set up default mock responses
    context.set_mock_response("get_page", Ok(mock_browser_page))
    context.set_mock_response("get_driver", Ok(mock_browser_driver))
    return context


@pytest.fixture
def mock_html_response() -> str:
    """Fixture to provide sample HTML response for tests."""
    return """
    <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Test Header</h1>
            <div class="container">
                <p>This is a test paragraph.</p>
                <button id="test-button">Click Me</button>
                <input type="text" id="test-input" placeholder="Enter text">
                <select id="test-select">
                    <option value="option1">Option 1</option>
                    <option value="option2">Option 2</option>
                </select>
                <table id="test-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Age</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>John</td>
                            <td>30</td>
                        </tr>
                        <tr>
                            <td>Jane</td>
                            <td>25</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def mock_selector() -> Selector:
    """Fixture to create a mock Selector."""
    return Selector("css", "#test-selector")


@pytest.fixture
def mock_selector_group() -> SelectorGroup:
    """Fixture to create a mock SelectorGroup."""
    return SelectorGroup(
        "test_group",
        Selector("css", "#primary-selector"),
        Selector("css", "#secondary-selector")
    )
    