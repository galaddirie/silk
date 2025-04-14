"""
Tests for Silk navigation actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from expression.core import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.navigation import (
    Navigate, GoBack, GoForward, Reload, WaitForNavigation,
    Screenshot, GetCurrentUrl, GetPageSource, ExecuteScript, WaitForSelector
)
from silk.browsers.types import NavigationOptions, WaitOptions
from silk.selectors.selector import Selector, SelectorGroup


# -------------------- Helper Functions for Testing --------------------

async def create_test_action_context(mock_driver=None, mock_page=None):
    """Create a context with mocked driver and page for testing actions"""
    context = MagicMock(spec=ActionContext)
    context.page_id = "test-page-id"
    
    if mock_driver:
        context.get_driver = AsyncMock(return_value=Ok(mock_driver))
    else:
        # Default implementation if no mock_driver provided
        context.get_driver = AsyncMock(return_value=Error(Exception("No driver provided")))
    
    if mock_page:
        context.get_page = AsyncMock(return_value=Ok(mock_page))
    
    return context


# -------------------- Navigation Action Tests --------------------

@pytest.mark.asyncio
async def test_navigate_success():
    """Test Navigate action with successful navigation"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.goto = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.goto.assert_called_once_with("test-page-id", "https://example.com")


@pytest.mark.asyncio
async def test_navigate_with_options():
    """Test Navigate action with navigation options"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.goto = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create navigation options
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    # Execute
    navigate = Navigate(url="https://example.com", options=options)
    result = await navigate(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.goto.assert_called_once_with("test-page-id", "https://example.com")


@pytest.mark.asyncio
async def test_navigate_no_page_id():
    """Test Navigate action with no page ID"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Create context with mocked driver but no page_id
    context = await create_test_action_context(mock_driver)
    context.page_id = None
    
    # Execute
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=context)
    
    # Assert
    assert result.is_error()
    assert "No browser page found" in str(result.error)


@pytest.mark.asyncio
async def test_go_back_success():
    """Test GoBack action with successful navigation"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.go_back = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    go_back = GoBack()
    result = await go_back(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.go_back.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_go_back_with_options():
    """Test GoBack action with navigation options"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.go_back = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create navigation options
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    # Execute
    go_back = GoBack(options=options)
    result = await go_back(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.go_back.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_go_forward_success():
    """Test GoForward action with successful navigation"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.go_forward = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    go_forward = GoForward()
    result = await go_forward(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.go_forward.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_reload_success():
    """Test Reload action with successful reload"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.reload = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    reload_action = Reload()
    result = await reload_action(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.reload.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_wait_for_navigation_success():
    """Test WaitForNavigation action successful completion"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_navigation = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    wait_for_navigation = WaitForNavigation()
    result = await wait_for_navigation(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_navigation.assert_called_once_with("test-page-id", None)


@pytest.mark.asyncio
async def test_wait_for_navigation_with_options():
    """Test WaitForNavigation action with options"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_navigation = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create navigation options
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    # Execute
    wait_for_navigation = WaitForNavigation(options=options)
    result = await wait_for_navigation(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_navigation.assert_called_once_with("test-page-id", options)


@pytest.mark.asyncio
async def test_screenshot_success():
    """Test Screenshot action with successful capture"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.screenshot = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create a temp path
    screenshot_path = Path("/path/to/screenshot.png")
    
    # Execute
    screenshot = Screenshot(path=screenshot_path)
    result = await screenshot(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == screenshot_path
    mock_driver.screenshot.assert_called_once_with("test-page-id", screenshot_path)


@pytest.mark.asyncio
async def test_get_current_url_success():
    """Test GetCurrentUrl action with successful retrieval"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.current_url = AsyncMock(return_value=Ok("https://example.com/page"))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    get_current_url = GetCurrentUrl()
    result = await get_current_url(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "https://example.com/page"
    mock_driver.current_url.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_get_current_url_failure():
    """Test GetCurrentUrl action with retrieval failure"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks to return an error
    mock_driver.current_url = AsyncMock(return_value=Error(Exception("Failed to get URL")))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    get_current_url = GetCurrentUrl()
    result = await get_current_url(context=context)
    
    # Assert
    assert result.is_error()
    assert "Failed to get URL" in str(result.error)


@pytest.mark.asyncio
async def test_get_page_source_success():
    """Test GetPageSource action with successful retrieval"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    html_source = "<html><body>Test page</body></html>"
    mock_driver.get_source = AsyncMock(return_value=Ok(html_source))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    get_page_source = GetPageSource()
    result = await get_page_source(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == html_source
    mock_driver.get_source.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_get_page_source_failure():
    """Test GetPageSource action with retrieval failure"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks to return an error
    mock_driver.get_source = AsyncMock(return_value=Error(Exception("Failed to get source")))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    get_page_source = GetPageSource()
    result = await get_page_source(context=context)
    
    # Assert
    assert result.is_error()
    assert "Failed to get source" in str(result.error)


@pytest.mark.asyncio
async def test_execute_script_success():
    """Test ExecuteScript action with successful execution"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    script_result = {"key": "value"}
    mock_driver.execute_script = AsyncMock(return_value=script_result)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    script = "return {'key': 'value'};"
    execute_script = ExecuteScript(script=script)
    result = await execute_script(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == script_result
    mock_driver.execute_script.assert_called_once_with("test-page-id", script)


@pytest.mark.asyncio
async def test_execute_script_with_args():
    """Test ExecuteScript action with arguments"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    script_result = "arg value: test"
    mock_driver.execute_script = AsyncMock(return_value=script_result)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    script = "return 'arg value: ' + arguments[0];"
    execute_script = ExecuteScript(script=script, args=("test",))
    result = await execute_script(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == script_result
    mock_driver.execute_script.assert_called_once_with("test-page-id", script, "test")


@pytest.mark.asyncio
async def test_wait_for_selector_with_string():
    """Test WaitForSelector action with string selector"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    wait_for_selector = WaitForSelector(selector="#test-element")
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#test-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_object():
    """Test WaitForSelector action with Selector object"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create a selector object
    selector = Selector(value="#test-element", type="css")
    
    # Execute
    wait_for_selector = WaitForSelector(selector=selector)
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#test-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_group():
    """Test WaitForSelector action with SelectorGroup"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create a selector group
    selector1 = Selector(value="#element1", type="css")
    selector2 = Selector(value="#element2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    # Execute
    wait_for_selector = WaitForSelector(selector=selector_group)
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#element1", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_empty_selector_group():
    """Test WaitForSelector action with empty SelectorGroup"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create an empty selector group
    selector_group = SelectorGroup("empty")
    
    # Execute
    wait_for_selector = WaitForSelector(selector=selector_group)
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_error()
    assert "Empty selector group" in str(result.error)


@pytest.mark.asyncio
async def test_wait_for_selector_with_options():
    """Test WaitForSelector action with wait options"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=None)
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create wait options
    options = WaitOptions(timeout=5000, visible=True)
    
    # Execute
    wait_for_selector = WaitForSelector(selector="#test-element", options=options)
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#test-element", options)


# -------------------- Error Case Tests --------------------

@pytest.mark.asyncio
async def test_navigate_no_driver():
    """Test Navigate action when no driver is available"""
    # Create context with no driver
    context = await create_test_action_context()  # No mock_driver provided
    
    # Execute
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=context)
    
    # Assert
    assert result.is_error()
    assert "No driver provided" in str(result.error)


@pytest.mark.asyncio
async def test_screenshot_driver_error():
    """Test Screenshot action when driver throws an exception"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks to raise an exception
    mock_driver.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    screenshot = Screenshot(path=Path("/path/to/screenshot.png"))
    result = await screenshot(context=context)
    
    # Assert
    assert result.is_error()
    assert "Screenshot failed" in str(result.error)


# -------------------- Integration Tests (Sequential Actions) --------------------

@pytest.mark.asyncio
async def test_navigate_then_get_url_sequential():
    """Test sequential operations: Navigate followed by GetCurrentUrl"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.goto = AsyncMock(return_value=None)
    mock_driver.current_url = AsyncMock(return_value=Ok("https://example.com"))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute Navigate operation
    navigate = Navigate(url="https://example.com")
    navigate_result = await navigate(context=context)
    assert navigate_result.is_ok()
    
    # Execute GetCurrentUrl operation
    get_current_url = GetCurrentUrl()
    get_url_result = await get_current_url(context=context)
    
    # Assert
    assert get_url_result.is_ok()
    assert get_url_result.default_value(None) == "https://example.com"
    
    # Verify both actions were called
    mock_driver.goto.assert_called_once_with("test-page-id", "https://example.com")
    mock_driver.current_url.assert_called_once_with("test-page-id")


@pytest.mark.asyncio
async def test_complex_navigation_sequence():
    """Test a complex sequence of navigation operations"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.goto = AsyncMock(return_value=None)
    mock_driver.wait_for_selector = AsyncMock(return_value=None)
    mock_driver.execute_script = AsyncMock(return_value="Script executed")
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # 1. Navigate to page
    navigate = Navigate(url="https://example.com")
    navigate_result = await navigate(context=context)
    assert navigate_result.is_ok()
    
    # 2. Wait for selector
    wait = WaitForSelector(selector="#content")
    wait_result = await wait(context=context)
    assert wait_result.is_ok()
    
    # 3. Execute script
    script = ExecuteScript(script="return document.title;")
    script_result = await script(context=context)
    
    # Assert final result
    assert script_result.is_ok()
    assert script_result.default_value(None) == "Script executed"
    
    # Verify all actions were called in sequence
    mock_driver.goto.assert_called_once_with("test-page-id", "https://example.com")
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#content", None)
    mock_driver.execute_script.assert_called_once_with("test-page-id", "return document.title;")