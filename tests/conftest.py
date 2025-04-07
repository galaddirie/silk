"""
Pytest fixtures for the Silk browser automation framework.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from expression.core import Error, Ok

from silk.browsers.context import BrowserContext, BrowserPage
from silk.browsers.driver import BrowserDriver
from silk.browsers.element import ElementHandle
from silk.browsers.manager import BrowserManager
from silk.browsers.drivers.playwright import PlaywrightDriver, PlaywrightElementHandle
from silk.models.browser import ActionContext, BrowserOptions

# todo remove async_ok and async_error with AsyncMock(Ok(value)) and AsyncMock(Error(error))
# Helper functions to create awaitable results
async def async_ok(value):
    return Ok(value)


async def async_error(error):
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
    mock.get_bounding_box = AsyncMock(return_value=Ok(
        {"x": 10, "y": 20, "width": 100, "height": 50}
    ))
    mock.click = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.is_visible = AsyncMock(return_value=Ok(True))
    mock.is_enabled = AsyncMock(return_value=Ok(True))
    mock.get_parent = AsyncMock(return_value=Ok(None))  # Will be set in specific tests if needed
    mock.get_children = AsyncMock(return_value=Ok([]))  # Will be set in specific tests if needed
    mock.query_selector = AsyncMock(return_value=Ok(None))  # Will be set in specific tests if needed
    mock.query_selector_all = AsyncMock(return_value=Ok([]))  # Will be set in specific tests if needed
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
    mock.query_selector = AsyncMock(return_value=Ok(None))  # Will be set in specific tests
    mock.query_selector_all = AsyncMock(return_value=Ok([]))  # Will be set in specific tests
    mock.wait_for_selector = AsyncMock(return_value=Ok(None))  # Will be set in specific tests
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
    mock.get_element_bounding_box = AsyncMock(return_value=Ok(
        {"x": 10, "y": 20, "width": 100, "height": 50}
    ))
    mock.click_element = AsyncMock(return_value=Ok(None))
    mock.get_element_html = AsyncMock(return_value=Ok("<div>Mock Element HTML</div>"))
    mock.get_element_inner_text = AsyncMock(return_value=Ok("Mock Element Inner Text"))
    mock.extract_table = AsyncMock(return_value=Ok(
        [{"header1": "value1", "header2": "value2"}]
    ))

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
    mock.query_selector = AsyncMock(return_value=Ok(None))  # Set in specific tests
    mock.query_selector_all = AsyncMock(return_value=Ok([]))  # Set in specific tests
    mock.execute_script = AsyncMock(return_value=Ok({"result": "mock-result"}))
    mock.wait_for_selector = AsyncMock(return_value=Ok(None))  # Set in specific tests
    mock.wait_for_navigation = AsyncMock(return_value=Ok(None))
    mock.screenshot = AsyncMock(return_value=Ok(Path("mock_screenshot.png")))
    mock.get_page_source = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
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

    # Special handling for execute_action as it needs to call the action
    async def async_execute_action(action):
        return await action.execute(
            ActionContext(
                browser_manager=mock,
                context_id="mock-context-id",
                page_id="mock-page-id",
            )
        )

    mock.execute_action.side_effect = async_execute_action

    return mock


@pytest.fixture
def action_context(mock_browser_manager) -> ActionContext:
    """Fixture to create an ActionContext for testing."""
    return ActionContext(
        browser_manager=mock_browser_manager,
        context_id="mock-context-id",
        page_id="mock-page-id",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )


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


# Add the playwright_driver fixture needed for TestPlaywrightElementHandleUnit
@pytest.fixture
def playwright_driver(browser_options) -> MagicMock:
    """Fixture to create a mock PlaywrightDriver instance."""
    mock = MagicMock(spec=PlaywrightDriver)
    mock.options = browser_options
    mock.initialized = False
    mock.contexts = {}
    mock.pages = {}

    # Mock playwright instance
    mock_playwright = MagicMock()
    mock.playwright = mock_playwright

    # Mock browser instance
    mock_browser = MagicMock()
    mock.browser = mock_browser

    # Mock async methods with awaitable results
    mock.launch = AsyncMock(return_value=Ok(None))
    mock.close = AsyncMock(return_value=Ok(None))
    mock.create_context = AsyncMock(return_value=Ok("mock-context-id"))
    mock.close_context = AsyncMock(return_value=Ok(None))
    mock.create_page = AsyncMock(return_value=Ok("mock-page-id"))
    mock.close_page = AsyncMock(return_value=Ok(None))
    mock.goto = AsyncMock(return_value=Ok(None))
    mock.current_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.get_source = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
    mock.screenshot = AsyncMock(return_value=Ok(b"mock-screenshot-bytes"))
    mock.reload = AsyncMock(return_value=Ok(None))
    mock.go_back = AsyncMock(return_value=Ok(None))
    mock.go_forward = AsyncMock(return_value=Ok(None))
    
    # Mock element interaction methods
    mock.query_selector = AsyncMock()
    mock.query_selector_all = AsyncMock()
    mock.wait_for_selector = AsyncMock()
    mock.wait_for_navigation = AsyncMock(return_value=Ok(None))
    mock.click = AsyncMock(return_value=Ok(None))
    mock.double_click = AsyncMock(return_value=Ok(None))
    mock.type = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.execute_script = AsyncMock(return_value=Ok("mock-script-result"))
    
    # Mock mouse and keyboard methods
    mock.mouse_move = AsyncMock(return_value=Ok(None))
    mock.mouse_down = AsyncMock(return_value=Ok(None))
    mock.mouse_up = AsyncMock(return_value=Ok(None))
    mock.mouse_click = AsyncMock(return_value=Ok(None))
    mock.mouse_double_click = AsyncMock(return_value=Ok(None))
    mock.mouse_drag = AsyncMock(return_value=Ok(None))
    mock.key_press = AsyncMock(return_value=Ok(None))
    mock.key_down = AsyncMock(return_value=Ok(None))
    mock.key_up = AsyncMock(return_value=Ok(None))
    
    # Element methods
    mock.get_element_text = AsyncMock(return_value=Ok("Mock Text"))
    mock.get_element_attribute = AsyncMock(return_value=Ok("mock-attribute"))
    mock.get_element_bounding_box = AsyncMock(return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50}))
    mock.click_element = AsyncMock(return_value=Ok(None))
    
    return mock


@pytest.fixture
def element_handle(playwright_driver) -> PlaywrightElementHandle:
    """Fixture to create a PlaywrightElementHandle with a mocked element reference."""
    mock_element_ref = MagicMock()
    
    # Add necessary async methods to the element_ref
    mock_element_ref.text_content = AsyncMock(return_value="Test Text")
    mock_element_ref.get_attribute = AsyncMock(return_value="attribute-value")
    mock_element_ref.click = AsyncMock()
    mock_element_ref.fill = AsyncMock()
    mock_element_ref.is_visible = AsyncMock(return_value=True)
    mock_element_ref.bounding_box = AsyncMock(return_value={"x": 10, "y": 20, "width": 100, "height": 50})
    
    element_handle = PlaywrightElementHandle(
        driver=playwright_driver,
        page_id="test-page",
        element_ref=mock_element_ref,
        selector="#test-element"
    )
    
    return element_handle


# Use this fixture to create a real BrowserManager for integration tests
# This can be used selectively by marking tests with @pytest.mark.integration
@pytest.fixture
async def real_browser_manager() -> AsyncGenerator[BrowserManager, None]:
    """
    Create a real BrowserManager for integration tests.
    """
    # Use a flag/marker instead of an environment variable
    if not os.environ.get("INTEGRATION_TESTS"):
        pytest.skip("Skipping integration test. Set INTEGRATION_TESTS=1 to run.")

    # Create a real browser manager with default options
    manager = BrowserManager(
        driver_type="playwright",
        default_options=BrowserOptions(
            headless=True,
            timeout=10000,
            viewport_width=1280,
            viewport_height=720,
        ),
    )

    try:
        yield manager
    finally:
        # Clean up after test
        await manager.close_all()


# Create a helper fixture for real browser context
@pytest.fixture
async def real_browser_context(
    real_browser_manager,
) -> AsyncGenerator[BrowserContext, None]:
    """Create a real browser context for integration tests."""
    context_result = await real_browser_manager.create_context()
    if context_result.is_error():
        pytest.fail(f"Failed to create browser context: {context_result.error}")

    context = context_result.default_value(None)
    if context is None:
        pytest.fail("Failed to create browser context")

    try:
        yield context
    finally:
        await real_browser_manager.close_context(context.id)


# Create a helper fixture for real browser page
@pytest.fixture
async def real_browser_page(real_browser_context) -> AsyncGenerator[BrowserPage, None]:
    """Create a real browser page for integration tests."""
    page_result = await real_browser_context.create_page()
    if page_result.is_error():
        pytest.fail(f"Failed to create browser page: {page_result.error}")

    page = page_result.default_value(None)
    if page is None:
        pytest.fail("Failed to create browser page")

    try:
        yield page
    finally:
        await page.close()