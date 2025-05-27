"""
Tests for Silk navigation actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from expression import Error, Ok, Result

from silk.actions.navigation import (
    Navigate, GoBack, GoForward, Reload, WaitForNavigation,
    Screenshot, GetCurrentUrl, GetPageSource, ExecuteScript, WaitForSelector
)
from silk.browsers.models import NavigationOptions, WaitOptions, ActionContext
from silk.selectors.selector import Selector, SelectorGroup


@pytest.mark.asyncio
async def test_navigate_success(action_context: ActionContext):
    """Test Navigate action with successful navigation"""
    action_context.driver.goto = AsyncMock(return_value=None)
    
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=action_context)
    
    assert result.is_ok()
    action_context.driver.goto.assert_called_once_with(action_context.page_id, "https://example.com")


@pytest.mark.asyncio
async def test_navigate_with_options(action_context: ActionContext):
    """Test Navigate action with navigation options"""
    action_context.driver.goto = AsyncMock(return_value=None)
    
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    navigate = Navigate(url="https://example.com", options=options)
    result = await navigate(context=action_context)
    
    assert result.is_ok()
    action_context.driver.goto.assert_called_once_with(action_context.page_id, "https://example.com")


@pytest.mark.asyncio
async def test_navigate_no_page_id(action_context: ActionContext):
    """Test Navigate action with no page ID"""
    action_context.page_id = None
    
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=action_context)
    
    assert result.is_error()
    assert "No page found" in str(result.error)


@pytest.mark.asyncio
async def test_go_back_success(action_context: ActionContext):
    """Test GoBack action with successful navigation"""
    action_context.driver.go_back = AsyncMock(return_value=None)
    
    go_back = GoBack()
    result = await go_back(context=action_context)
    
    assert result.is_ok()
    action_context.driver.go_back.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_go_back_with_options(action_context: ActionContext):
    """Test GoBack action with navigation options"""
    action_context.driver.go_back = AsyncMock(return_value=None)
    
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    go_back = GoBack(options=options)
    result = await go_back(context=action_context)
    
    assert result.is_ok()
    action_context.driver.go_back.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_go_forward_success(action_context: ActionContext):
    """Test GoForward action with successful navigation"""
    action_context.driver.go_forward = AsyncMock(return_value=None)
    
    go_forward = GoForward()
    result = await go_forward(context=action_context)
    
    assert result.is_ok()
    action_context.driver.go_forward.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_reload_success(action_context: ActionContext):
    """Test Reload action with successful reload"""
    action_context.driver.reload = AsyncMock(return_value=None)
    
    reload_action = Reload()
    result = await reload_action(context=action_context)
    
    assert result.is_ok()
    action_context.driver.reload.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_wait_for_navigation_success(action_context: ActionContext):
    """Test WaitForNavigation action successful completion"""
    action_context.driver.wait_for_navigation = AsyncMock(return_value=None)
    
    wait_for_navigation = WaitForNavigation()
    result = await wait_for_navigation(context=action_context)
    
    assert result.is_ok()
    action_context.driver.wait_for_navigation.assert_called_once_with(action_context.page_id, None)


@pytest.mark.asyncio
async def test_wait_for_navigation_with_options(action_context: ActionContext):
    """Test WaitForNavigation action with options"""
    action_context.driver.wait_for_navigation = AsyncMock(return_value=None)
    
    options = NavigationOptions(timeout=5000, wait_until="networkidle")
    
    wait_for_navigation = WaitForNavigation(options=options)
    result = await wait_for_navigation(context=action_context)
    
    assert result.is_ok()
    action_context.driver.wait_for_navigation.assert_called_once_with(action_context.page_id, options)


@pytest.mark.asyncio
async def test_screenshot_success(action_context: ActionContext):
    """Test Screenshot action with successful capture"""
    action_context.driver.screenshot = AsyncMock(return_value=None)
    
    screenshot_path = Path("/path/to/screenshot.png")
    
    screenshot = Screenshot(path=screenshot_path)
    result = await screenshot(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == screenshot_path
    action_context.driver.screenshot.assert_called_once_with(action_context.page_id, screenshot_path)


@pytest.mark.asyncio
async def test_get_current_url_success(action_context: ActionContext):
    """Test GetCurrentUrl action with successful retrieval"""
    action_context.driver.current_url = AsyncMock(return_value=Ok("https://example.com/page"))
    
    get_current_url = GetCurrentUrl()
    result = await get_current_url(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "https://example.com/page"
    action_context.driver.current_url.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_get_current_url_failure(action_context: ActionContext):
    """Test GetCurrentUrl action with retrieval failure"""
    action_context.driver.current_url = AsyncMock(return_value=Error(Exception("Failed to get URL")))
    
    get_current_url = GetCurrentUrl()
    result = await get_current_url(context=action_context)
    
    assert result.is_error()
    assert "Failed to get URL" in str(result.error)


@pytest.mark.asyncio
async def test_get_page_source_success(action_context: ActionContext):
    """Test GetPageSource action with successful retrieval"""
    html_source = "<html><body>Test page</body></html>"
    action_context.driver.get_source = AsyncMock(return_value=Ok(html_source))
    
    get_page_source = GetPageSource()
    result = await get_page_source(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == html_source
    action_context.driver.get_source.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_get_page_source_failure(action_context: ActionContext):
    """Test GetPageSource action with retrieval failure"""
    action_context.driver.get_source = AsyncMock(return_value=Error(Exception("Failed to get source")))
    
    get_page_source = GetPageSource()
    result = await get_page_source(context=action_context)
    
    assert result.is_error()
    assert "Failed to get source" in str(result.error)


@pytest.mark.asyncio
async def test_execute_script_success(action_context: ActionContext):
    """Test ExecuteScript action with successful execution"""
    script_result = {"key": "value"}
    action_context.driver.execute_script = AsyncMock(return_value=script_result)
    
    script = "return {'key': 'value'};"
    execute_script = ExecuteScript(script=script)
    result = await execute_script(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == script_result
    action_context.driver.execute_script.assert_called_once_with(action_context.page_id, script)


@pytest.mark.asyncio
async def test_execute_script_with_args(action_context: ActionContext):
    """Test ExecuteScript action with arguments"""
    script_result = "arg value: test"
    action_context.driver.execute_script = AsyncMock(return_value=script_result)
    
    script = "return 'arg value: ' + arguments[0];"
    execute_script = ExecuteScript(script=script, args=("test",))
    result = await execute_script(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == script_result
    action_context.driver.execute_script.assert_called_once_with(action_context.page_id, script, "test")


@pytest.mark.asyncio
async def test_wait_for_selector_with_string(action_context: ActionContext):
    """Test WaitForSelector action with string selector"""
    action_context.driver.wait_for_selector = AsyncMock(return_value=None)
    
    wait_for_selector = WaitForSelector(selector="#test-element")
    result = await wait_for_selector(context=action_context)
    
    assert result.is_ok()
    action_context.driver.wait_for_selector.assert_called_once_with(action_context.page_id, "#test-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_object(action_context: ActionContext):
    """Test WaitForSelector action with Selector object"""
    action_context.driver.wait_for_selector = AsyncMock(return_value=None)
    selector = Selector(value="#test-element", type="css")
    wait_for_selector = WaitForSelector(selector=selector)
    result = await wait_for_selector(context=action_context)
    assert result.is_ok()
    action_context.driver.wait_for_selector.assert_called_once_with(action_context.page_id, "#test-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_group(action_context: ActionContext):
    """Test WaitForSelector action with SelectorGroup"""
    action_context.driver.wait_for_selector = AsyncMock(return_value=None)
    selector1 = Selector(value="#element1", type="css")
    selector2 = Selector(value="#element2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    wait_for_selector = WaitForSelector(selector=selector_group)
    result = await wait_for_selector(context=action_context)
    assert result.is_ok()
    action_context.driver.wait_for_selector.assert_called_once_with(action_context.page_id, "#element1", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_empty_selector_group(action_context: ActionContext):
    """Test WaitForSelector action with empty SelectorGroup"""
    selector_group = SelectorGroup("empty")
    wait_for_selector = WaitForSelector(selector=selector_group)
    result = await wait_for_selector(context=action_context)
    assert result.is_error()
    assert "Empty selector group" in str(result.error)


@pytest.mark.asyncio
async def test_wait_for_selector_with_options(action_context: ActionContext):
    """Test WaitForSelector action with wait options"""
    action_context.driver.wait_for_selector = AsyncMock(return_value=None)
    options = WaitOptions(timeout=5000, visible=True)
    wait_for_selector = WaitForSelector(selector="#test-element", options=options)
    result = await wait_for_selector(context=action_context)
    assert result.is_ok()
    action_context.driver.wait_for_selector.assert_called_once_with(action_context.page_id, "#test-element", options)


@pytest.mark.asyncio
async def test_navigate_no_driver(action_context: ActionContext):
    """Test Navigate action when no driver is available in the context"""
    action_context.driver = None 
    navigate = Navigate(url="https://example.com")
    result = await navigate(context=action_context)
    assert result.is_error()
    assert "No driver found" in str(result.error)


@pytest.mark.asyncio
async def test_screenshot_driver_error(action_context: ActionContext):
    """Test Screenshot action when driver throws an exception"""
    action_context.driver.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))
    screenshot = Screenshot(path=Path("/path/to/screenshot.png"))
    result = await screenshot(context=action_context)
    assert result.is_error()
    assert "Screenshot failed" in str(result.error)


@pytest.mark.asyncio
async def test_navigate_then_get_url_sequential(action_context: ActionContext):
    """Test sequential operations: Navigate followed by GetCurrentUrl"""
    action_context.driver.goto = AsyncMock(return_value=None)
    action_context.driver.current_url = AsyncMock(return_value=Ok("https://example.com"))
    navigate = Navigate(url="https://example.com")
    navigate_result = await navigate(context=action_context)
    assert navigate_result.is_ok()
    get_current_url = GetCurrentUrl()
    get_url_result = await get_current_url(context=action_context)
    assert get_url_result.is_ok()
    assert get_url_result.default_value(None) == "https://example.com"
    action_context.driver.goto.assert_called_once_with(action_context.page_id, "https://example.com")
    action_context.driver.current_url.assert_called_once_with(action_context.page_id)


@pytest.mark.asyncio
async def test_complex_navigation_sequence(action_context: ActionContext):
    """Test a complex sequence of navigation operations"""
    action_context.driver.goto = AsyncMock(return_value=None)
    action_context.driver.wait_for_selector = AsyncMock(return_value=None)
    action_context.driver.execute_script = AsyncMock(return_value="Script executed")
    navigate = Navigate(url="https://example.com")
    navigate_result = await navigate(context=action_context)
    assert navigate_result.is_ok()
    wait = WaitForSelector(selector="#content")
    wait_result = await wait(context=action_context)
    assert wait_result.is_ok()
    script_action = ExecuteScript(script="return document.title;")
    script_result = await script_action(context=action_context)
    assert script_result.is_ok()
    assert script_result.default_value(None) == "Script executed"
    action_context.driver.goto.assert_called_once_with(action_context.page_id, "https://example.com")
    action_context.driver.wait_for_selector.assert_called_once_with(action_context.page_id, "#content", None)
    action_context.driver.execute_script.assert_called_once_with(action_context.page_id, "return document.title;")