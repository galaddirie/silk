"""
Pytest fixtures for the Silk browser automation framework.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, create_autospec
from contextlib import asynccontextmanager

import pytest
from expression import Error, Ok, Result

from silk.browsers.models import (
    ActionContext, 
    BrowserOptions,
    ElementHandle,
    Page,
    BrowserContext,
    Driver,
    MouseOptions,
    TypeOptions,
    NavigationOptions,
    WaitOptions,
    SelectOptions,
    DragOptions,
    CoordinateType,
)
from silk.browsers.sessions import BrowserSession
from silk.selectors.selector import Selector, SelectorGroup


async def async_ok(value):
    """Create an awaitable Ok result."""
    return Ok(value)


async def async_error(error):
    """Create an awaitable Error result."""
    return Error(error)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_element_handle() -> MagicMock:
    """Fixture to create a mock ElementHandle that implements the protocol."""
    mock = create_autospec(ElementHandle, instance=True)
    
    mock.driver = create_autospec(Driver, instance=True)
    mock.page_id = "mock-page-id"
    mock.context_id = "mock-context-id"
    mock.selector = "#mock-selector"
    mock.element_ref = "mock-element-ref"
    
    mock.get_page_id = MagicMock(return_value="mock-page-id")
    mock.get_context_id = MagicMock(return_value="mock-context-id")
    mock.get_selector = MagicMock(return_value="#mock-selector")
    mock.get_element_ref = MagicMock(return_value="mock-element-ref")
    
    mock.click = AsyncMock(return_value=Ok(None))
    mock.double_click = AsyncMock(return_value=Ok(None))
    mock.type = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.get_text = AsyncMock(return_value=Ok("Mock Text"))
    mock.text = AsyncMock(return_value="Mock Text")
    mock.get_inner_text = AsyncMock(return_value=Ok("Mock Inner Text"))
    mock.get_html = AsyncMock(return_value=Ok("<div>Mock HTML</div>"))
    mock.get_attribute = AsyncMock(return_value=Ok("mock-attribute"))
    mock.attribute = AsyncMock(return_value="mock-attribute")
    mock.has_attribute = AsyncMock(return_value=True)
    mock.get_property = AsyncMock(return_value=Ok("mock-property"))
    mock.get_bounding_box = AsyncMock(
        return_value=Ok({"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0})
    )
    mock.is_visible = AsyncMock(return_value=Ok(True))
    mock.is_enabled = AsyncMock(return_value=Ok(True))
    mock.get_parent = AsyncMock(return_value=Ok(None))
    mock.get_children = AsyncMock(return_value=Ok([]))
    mock.query_selector = AsyncMock(return_value=Ok(None))
    mock.query_selector_all = AsyncMock(return_value=Ok([]))
    mock.scroll_into_view = AsyncMock(return_value=Ok(None))
    
    # For methods that return `self` (the mock instance itself)
    mock.input = AsyncMock(return_value=mock)
    mock.choose = AsyncMock(return_value=mock)
    
    # For async context managers, mock the __aenter__ and __aexit__ methods
    # if direct async call is not sufficient.
    # For simple cases, AsyncMock might be enough if the protocol doesn't strictly enforce it.
    # If with_scroll_into_view is an async context manager:
    # mock_context_manager = AsyncMock()
    # mock_context_manager.__aenter__.return_value = mock
    # mock_context_manager.__aexit__.return_value = None
    # mock.with_scroll_into_view = MagicMock(return_value=mock_context_manager)
    # Or more simply if the context manager itself is awaitable and returns the element
    
    async def mock_with_scroll_into_view_gen():
        yield mock
    
    mock.with_scroll_into_view = MagicMock(return_value=asynccontextmanager(mock_with_scroll_into_view_gen)())

    mock.as_native = MagicMock(return_value="mock-element-ref")
    
    return mock


@pytest.fixture
def mock_page(mock_element_handle) -> MagicMock:
    """Fixture to create a mock Page that implements the protocol."""
    mock = create_autospec(Page, instance=True)
    
    mock.page_id = "mock-page-id"
    mock.page_ref = "mock-page-ref"
    
    mock.get_page_id = MagicMock(return_value="mock-page-id")
    
    mock.goto = AsyncMock(return_value=Ok(None))
    mock.get_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.current_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.get_title = AsyncMock(return_value=Ok("Mock Page Title"))
    mock.get_content = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
    mock.get_page_source = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
    mock.reload = AsyncMock(return_value=Ok(None))
    mock.go_back = AsyncMock(return_value=Ok(None))
    mock.go_forward = AsyncMock(return_value=Ok(None))
    mock.query_selector = AsyncMock(return_value=Ok(mock_element_handle))
    mock.query_selector_all = AsyncMock(return_value=Ok([mock_element_handle]))
    mock.wait_for_selector = AsyncMock(return_value=Ok(mock_element_handle))
    mock.wait_for_navigation = AsyncMock(return_value=Ok(None))
    mock.click = AsyncMock(return_value=Ok(None))
    mock.double_click = AsyncMock(return_value=Ok(None))
    mock.type = AsyncMock(return_value=Ok(None))
    mock.fill = AsyncMock(return_value=Ok(None))
    mock.select = AsyncMock(return_value=Ok(None))
    mock.execute_script = AsyncMock(return_value=Ok({"result": "mock-result"}))
    mock.screenshot = AsyncMock(return_value=Ok(Path("mock_screenshot.png")))
    mock.mouse_move = AsyncMock(return_value=Ok(None))
    mock.mouse_down = AsyncMock(return_value=Ok(None))
    mock.mouse_up = AsyncMock(return_value=Ok(None))
    mock.mouse_click = AsyncMock(return_value=Ok(None))
    mock.mouse_drag = AsyncMock(return_value=Ok(None))
    mock.key_press = AsyncMock(return_value=Ok(None))
    mock.key_down = AsyncMock(return_value=Ok(None))
    mock.key_up = AsyncMock(return_value=Ok(None))
    mock.close = AsyncMock(return_value=Ok(None))
    mock.scroll = AsyncMock(return_value=Ok(None))
    
    return mock


@pytest.fixture
def mock_browser_context(mock_page) -> MagicMock:
    """Fixture to create a mock BrowserContext that implements the protocol."""
    mock = create_autospec(BrowserContext, instance=True)
    
    # Attributes defined in the BrowserContext protocol (src/silk/browsers/models.py)
    mock.page_id = "mock-context-page-id"  # As per current protocol (BrowserContext.page_id)
    mock.context_ref = "mock-context-ref" # As per current protocol (BrowserContext.context_ref)

    # Add the 'context_id' attribute that the CreateContext action expects.
    # This is the primary fix for the "Mock object has no attribute 'context_id'" error.
    mock.context_id = "mock-context-id" 
    
    # Configure return values for methods defined in the BrowserContext protocol.
    # create_autospec stubs these methods, but their return_values need to be set.
    mock.get_page_id.return_value = "mock-context-page-id" # Corresponds to BrowserContext.get_page_id()

    mock.new_page.return_value = Ok(mock_page)
    mock.create_page.return_value = Ok(mock_page)
    mock.pages.return_value = Ok([mock_page])
    mock.get_page.return_value = Ok(mock_page)
    mock.close_page.return_value = Ok(None)
    mock.get_cookies.return_value = Ok([])
    mock.set_cookies.return_value = Ok(None)
    mock.clear_cookies.return_value = Ok(None)
    mock.add_init_script.return_value = Ok(None)
    mock.set_content.return_value = Ok(None)  # Added as it's in the protocol

    # Mouse methods
    mock.mouse_move.return_value = Ok(None)
    mock.mouse_down.return_value = Ok(None)
    mock.mouse_up.return_value = Ok(None)
    mock.mouse_click.return_value = Ok(None)
    mock.mouse_double_click.return_value = Ok(None)
    mock.mouse_drag.return_value = Ok(None)

    # Key methods
    mock.key_press.return_value = Ok(None)
    mock.key_down.return_value = Ok(None)
    mock.key_up.return_value = Ok(None)
    
    mock.close.return_value = Ok(None)
    
    return mock


@pytest.fixture
def mock_driver(mock_browser_context, mock_page, mock_element_handle) -> MagicMock:
    """Fixture to create a mock Driver that implements the protocol."""
    mock = create_autospec(Driver, instance=True)
    
    mock.driver_ref = "mock-driver-ref"
    
    mock.get_driver_ref = MagicMock(return_value="mock-driver-ref")
    
    mock.launch = AsyncMock(return_value=Ok(None))
    mock.new_context = AsyncMock(return_value=Ok(mock_browser_context))
    mock.create_context = AsyncMock(return_value=Ok("mock-context-id"))
    mock.contexts = AsyncMock(return_value=Ok([mock_browser_context]))
    mock.close_context = AsyncMock(return_value=Ok(None))
    mock.create_page = AsyncMock(return_value=Ok("mock-page-id"))
    mock.close_page = AsyncMock(return_value=Ok(None))
    mock.goto = AsyncMock(return_value=Ok(None))
    mock.current_url = AsyncMock(return_value=Ok("https://example.com"))
    mock.get_source = AsyncMock(return_value=Ok("<html><body>Mock page</body></html>"))
    mock.screenshot = AsyncMock(return_value=Ok(Path("mock_screenshot.png")))
    mock.reload = AsyncMock(return_value=Ok(None))
    mock.go_back = AsyncMock(return_value=Ok(None))
    mock.go_forward = AsyncMock(return_value=Ok(None))
    mock.query_selector = AsyncMock(return_value=Ok(mock_element_handle))
    mock.query_selector_all = AsyncMock(return_value=Ok([mock_element_handle]))
    mock.wait_for_selector = AsyncMock(return_value=Ok(mock_element_handle))
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
        return_value=Ok({"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0})
    )
    mock.click_element = AsyncMock(return_value=Ok(None))
    mock.get_element_html = AsyncMock(return_value=Ok("<div>Mock Element HTML</div>"))
    mock.get_element_inner_text = AsyncMock(return_value=Ok("Mock Element Inner Text"))

    mock.scroll = AsyncMock(return_value=Ok(None))
    mock.execute_cdp_cmd = AsyncMock(return_value=Ok({"result": "mock-cdp-result"}))
    mock.close = AsyncMock(return_value=Ok(None))
    
    return mock

@pytest.fixture
def browser_options() -> BrowserOptions:
    """Fixture to create browser options for testing."""
    return BrowserOptions(
        headless=True,
        timeout=5000,
        viewport_width=1280,
        viewport_height=720,
        stealth_mode=False,
    )


@pytest.fixture
def action_context(mock_driver, mock_browser_context, mock_page) -> ActionContext:
    """Fixture to create an ActionContext for testing."""
    return ActionContext(
        driver=mock_driver,
        context=mock_browser_context,
        page=mock_page,
        driver_type="mock",
        context_id="mock-context-id",
        page_id="mock-page-id",
        page_ids={"mock-page-id"},
        metadata={
            "browser_options": BrowserOptions().model_dump(),
            "context_options": {},
        }
    )


@pytest.fixture
async def mock_browser_session(
    browser_options, 
    mock_driver, 
    mock_browser_context, 
    mock_page,
    action_context
) -> AsyncGenerator[BrowserSession, None]:
    """Fixture to create a mock BrowserSession."""
    mock_driver_class = MagicMock()
    mock_driver_class.return_value = mock_driver
    
    session = BrowserSession(
        options=browser_options,
        driver_class=mock_driver_class,
        create_context=True,
        create_page=True,
    )
    
    session.driver = mock_driver
    session.browser_context = mock_browser_context
    session.page = mock_page
    session.context = action_context
    session._started = True
    
    yield session
    
    await session.close()


@pytest.fixture
def mock_mouse_options() -> MouseOptions:
    """Fixture to create MouseOptions for testing."""
    return MouseOptions(
        button="left",
        modifiers=[],
        steps=1,
        smooth=True,
        total_time=0.5,
        timeout=5000,
    )


@pytest.fixture
def mock_type_options() -> TypeOptions:
    """Fixture to create TypeOptions for testing."""
    return TypeOptions(
        delay=10,
        clear=False,
        timeout=5000,
    )


@pytest.fixture
def mock_navigation_options() -> NavigationOptions:
    """Fixture to create NavigationOptions for testing."""
    return NavigationOptions(
        wait_until="load",
        timeout=5000,
    )


@pytest.fixture
def mock_wait_options() -> WaitOptions:
    """Fixture to create WaitOptions for testing."""
    return WaitOptions(
        state="visible",
        poll_interval=100,
        timeout=5000,
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


@pytest.fixture
def failed_result() -> Result[None, Exception]:
    """Fixture that returns a failed Result."""
    return Error(Exception("Mock error"))


@pytest.fixture
def success_result() -> Result[None, Exception]:
    """Fixture that returns a successful Result."""
    return Ok(None)


@pytest.fixture
def mock_coordinates() -> CoordinateType:
    """Fixture for mock coordinates."""
    return (100, 200)


@pytest.fixture
def mock_driver_class(mock_driver):
    """Fixture to create a mock driver class."""
    mock_class = MagicMock()
    mock_class.return_value = mock_driver
    mock_class.__name__ = "MockDriver"
    return mock_class