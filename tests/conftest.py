"""
Pytest fixtures for the Silk browser automation framework.
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from expression.core import Error, Ok

from silk.browsers.context import BrowserContext, BrowserPage
from silk.browsers.driver import BrowserDriver
from silk.browsers.element import ElementHandle
from silk.browsers.manager import BrowserManager
from silk.models.browser import ActionContext, BrowserOptions


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
    mock.get_text.return_value = async_ok("Mock Text")
    mock.get_inner_text.return_value = async_ok("Mock Inner Text")
    mock.get_html.return_value = async_ok("<div>Mock HTML</div>")
    mock.get_attribute.return_value = async_ok("mock-attribute")
    mock.get_property.return_value = async_ok("mock-property")
    mock.get_bounding_box.return_value = async_ok(
        {"x": 10, "y": 20, "width": 100, "height": 50}
    )
    mock.click.return_value = async_ok(None)
    mock.fill.return_value = async_ok(None)
    mock.select.return_value = async_ok(None)
    mock.is_visible.return_value = async_ok(True)
    mock.is_enabled.return_value = async_ok(True)
    mock.get_parent.return_value = async_ok(
        None
    )  # Will be set in specific tests if needed
    mock.get_children.return_value = async_ok(
        []
    )  # Will be set in specific tests if needed
    mock.query_selector.return_value = async_ok(
        None
    )  # Will be set in specific tests if needed
    mock.query_selector_all.return_value = async_ok(
        []
    )  # Will be set in specific tests if needed
    mock.scroll_into_view.return_value = async_ok(None)

    # Set up non-async methods
    mock.get_selector.return_value = "#mock-selector"
    mock.get_page_id.return_value = "mock-page-id"

    return mock


@pytest.fixture
def mock_browser_driver() -> MagicMock:
    """Fixture to create a mock BrowserDriver."""
    mock = MagicMock(spec=BrowserDriver)

    # Mock async methods with awaitable Result returns
    mock.launch.return_value = async_ok(None)
    mock.close.return_value = async_ok(None)
    mock.create_context.return_value = async_ok("mock-context-id")
    mock.close_context.return_value = async_ok(None)
    mock.create_page.return_value = async_ok("mock-page-ref")
    mock.close_page.return_value = async_ok(None)
    mock.goto.return_value = async_ok(None)
    mock.current_url.return_value = async_ok("https://example.com")
    mock.get_source.return_value = async_ok("<html><body>Mock page</body></html>")
    mock.screenshot.return_value = async_ok(Path("mock_screenshot.png"))
    mock.reload.return_value = async_ok(None)
    mock.go_back.return_value = async_ok(None)
    mock.go_forward.return_value = async_ok(None)
    mock.query_selector.return_value = async_ok(None)  # Will be set in specific tests
    mock.query_selector_all.return_value = async_ok([])  # Will be set in specific tests
    mock.wait_for_selector.return_value = async_ok(
        None
    )  # Will be set in specific tests
    mock.wait_for_navigation.return_value = async_ok(None)
    mock.click.return_value = async_ok(None)
    mock.double_click.return_value = async_ok(None)
    mock.type.return_value = async_ok(None)
    mock.fill.return_value = async_ok(None)
    mock.select.return_value = async_ok(None)
    mock.execute_script.return_value = async_ok({"result": "mock-result"})
    mock.mouse_move.return_value = async_ok(None)
    mock.mouse_down.return_value = async_ok(None)
    mock.mouse_up.return_value = async_ok(None)
    mock.mouse_click.return_value = async_ok(None)
    mock.mouse_double_click.return_value = async_ok(None)
    mock.mouse_drag.return_value = async_ok(None)
    mock.key_press.return_value = async_ok(None)
    mock.key_down.return_value = async_ok(None)
    mock.key_up.return_value = async_ok(None)
    mock.get_element_text.return_value = async_ok("Mock Element Text")
    mock.get_element_attribute.return_value = async_ok("mock-element-attribute")
    mock.get_element_bounding_box.return_value = async_ok(
        {"x": 10, "y": 20, "width": 100, "height": 50}
    )
    mock.click_element.return_value = async_ok(None)
    mock.get_element_html.return_value = async_ok("<div>Mock Element HTML</div>")
    mock.get_element_inner_text.return_value = async_ok("Mock Element Inner Text")
    mock.extract_table.return_value = async_ok(
        [{"header1": "value1", "header2": "value2"}]
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
async def mock_browser_page(mock_browser_driver) -> MagicMock:
    """Fixture to create a mock BrowserPage."""
    mock = MagicMock(spec=BrowserPage)
    mock.id = "mock-page-id"
    mock.context_id = "mock-context-id"
    mock.driver = mock_browser_driver
    mock.page_ref = "mock-page-ref"

    # Mock the async methods with awaitable results
    mock.goto.return_value = async_ok(None)
    mock.current_url.return_value = async_ok("https://example.com")
    mock.reload.return_value = async_ok(None)
    mock.go_back.return_value = async_ok(None)
    mock.go_forward.return_value = async_ok(None)
    mock.close.return_value = async_ok(None)
    mock.query_selector.return_value = async_ok(None)  # Set in specific tests
    mock.query_selector_all.return_value = async_ok([])  # Set in specific tests
    mock.execute_script.return_value = async_ok({"result": "mock-result"})
    mock.wait_for_selector.return_value = async_ok(None)  # Set in specific tests
    mock.wait_for_navigation.return_value = async_ok(None)
    mock.screenshot.return_value = async_ok(Path("mock_screenshot.png"))
    mock.get_page_source.return_value = async_ok("<html><body>Mock page</body></html>")
    mock.click.return_value = async_ok(None)
    mock.fill.return_value = async_ok(None)
    mock.double_click.return_value = async_ok(None)
    mock.type.return_value = async_ok(None)
    mock.select.return_value = async_ok(None)

    return mock


@pytest.fixture
async def mock_browser_context(mock_browser_driver, mock_browser_page) -> MagicMock:
    """Fixture to create a mock BrowserContext."""
    mock = MagicMock(spec=BrowserContext)
    mock.id = "mock-context-id"
    mock.driver = mock_browser_driver
    mock.options = {}
    mock.context_ref = "mock-context-ref"
    mock.pages = {"mock-page-id": mock_browser_page}
    mock.default_page_id = "mock-page-id"

    # Mock the async methods with awaitable results
    mock.create_page.return_value = async_ok(mock_browser_page)
    mock.get_page.return_value = Ok(mock_browser_page)  # This one is not async
    mock.mouse_move.return_value = async_ok(None)
    mock.mouse_down.return_value = async_ok(None)
    mock.mouse_up.return_value = async_ok(None)
    mock.mouse_click.return_value = async_ok(None)
    mock.mouse_double_click.return_value = async_ok(None)
    mock.mouse_drag.return_value = async_ok(None)
    mock.key_press.return_value = async_ok(None)
    mock.key_down.return_value = async_ok(None)
    mock.key_up.return_value = async_ok(None)
    mock.close.return_value = async_ok(None)

    return mock


@pytest.fixture
async def mock_browser_manager(mock_browser_driver, mock_browser_context) -> MagicMock:
    """Fixture to create a mock BrowserManager."""
    mock = MagicMock(spec=BrowserManager)
    mock.default_options = BrowserOptions()
    mock.drivers = {"mock-context-id": mock_browser_driver}
    mock.contexts = {"mock-context-id": mock_browser_context}
    mock.default_context_id = "mock-context-id"

    # Mock the async methods with awaitable results
    mock.create_context.return_value = async_ok(mock_browser_context)
    mock.get_context.return_value = Ok(mock_browser_context)  # This one is not async
    mock.close_context.return_value = async_ok(None)
    mock.close_all.return_value = async_ok(None)

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


# Use this fixture to create a real BrowserManager for integration tests
# This can be used selectively by marking tests with @pytest.mark.integration
@pytest.fixture
async def real_browser_manager() -> AsyncGenerator[BrowserManager, None]:
    """
    Create a real BrowserManager for integration tests.
    """
    # todo use a flag/marker instead of an environment variable
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
