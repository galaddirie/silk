"""
Tests for Silk extraction actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression import Error, Ok, Result

from silk.actions.elements import (
    Query, QueryAll, GetText, GetAttribute, GetHtml, 
    GetInnerText, ExtractTable, WaitForSelector, ElementExists
)
from silk.browsers.models import ActionContext, ElementHandle, Page, WaitOptions
from silk.selectors.selector import Selector, SelectorGroup


def create_mock_element(selector="#test-selector", text="Test Text", html="<div>Test Text</div>"):
    """Create a mock element with common methods"""
    mock_element = MagicMock(spec=ElementHandle)
    
    mock_element.driver = MagicMock()
    mock_element.page_id = "test-page-id"
    mock_element.context_id = "test-context-id"
    mock_element.selector = selector
    mock_element.element_ref = "mock-element-ref"
    
    mock_element.get_selector = MagicMock(return_value=selector)
    mock_element.get_page_id = MagicMock(return_value="test-page-id")
    mock_element.get_context_id = MagicMock(return_value="test-context-id")
    mock_element.get_element_ref = MagicMock(return_value="mock-element-ref")
    
    mock_element.get_text = AsyncMock(return_value=Ok(text))
    mock_element.get_html = AsyncMock(return_value=Ok(html))
    mock_element.get_attribute = AsyncMock(side_effect=lambda attr: Ok(f"value-of-{attr}"))
    mock_element.query_selector_all = AsyncMock(return_value=Ok([]))
    
    return mock_element


@pytest.mark.asyncio
async def test_query_with_string_selector(action_context, mock_page):
    """Test Query action with a string selector"""
    mock_element = create_mock_element()
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    query = Query(selector="#test-selector")
    result = await query(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_query_with_selector_object(action_context, mock_page):
    """Test Query action with a Selector object"""
    mock_element = create_mock_element()
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    selector = Selector(value="#test-selector", type="css")
    
    query = Query(selector=selector)
    result = await query(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_query_with_selector_group(action_context, mock_page):
    """Test Query action with a SelectorGroup object"""
    mock_element = create_mock_element()
    
    mock_page.query_selector = AsyncMock()
    mock_page.query_selector.side_effect = [
        Ok(mock_element),
        Ok(None)
    ]
    
    action_context.page = mock_page
    
    selector1 = Selector(value="#element1", type="css")
    selector2 = Selector(value="#element2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    query = Query(selector=selector_group)
    result = await query(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    mock_page.query_selector.assert_called_once_with("#element1")


@pytest.mark.asyncio
async def test_query_all_with_string_selector(action_context, mock_page):
    """Test QueryAll action with a string selector"""
    mock_element1 = create_mock_element("#element1", "Text 1")
    mock_element2 = create_mock_element("#element2", "Text 2")
    
    mock_page.query_selector_all = AsyncMock(return_value=Ok([mock_element1, mock_element2]))
    
    action_context.page = mock_page
    
    query_all = QueryAll(selector=".test-elements")
    result = await query_all(context=action_context)
    
    assert result.is_ok()
    elements = result.default_value(None)
    assert len(elements) == 2
    assert elements[0] == mock_element1
    assert elements[1] == mock_element2
    mock_page.query_selector_all.assert_called_once_with(".test-elements")


@pytest.mark.asyncio
async def test_query_all_with_selector_group(action_context, mock_page):
    """Test QueryAll action with a SelectorGroup object"""
    mock_element1 = create_mock_element("#element1", "Text 1")
    mock_element2 = create_mock_element("#element2", "Text 2")
    mock_element3 = create_mock_element("#element3", "Text 3")
    
    mock_page.query_selector_all = AsyncMock()
    mock_page.query_selector_all.side_effect = [
        Ok([mock_element1]),
        Ok([mock_element2, mock_element3])
    ]
    
    action_context.page = mock_page
    
    selector1 = Selector(value=".group1", type="css")
    selector2 = Selector(value=".group2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    query_all = QueryAll(selector=selector_group)
    result = await query_all(context=action_context)
    
    assert result.is_ok()
    elements = result.default_value(None)
    assert len(elements) == 3
    assert elements[0] == mock_element1
    assert elements[1] == mock_element2
    assert elements[2] == mock_element3
    assert mock_page.query_selector_all.call_count == 2
    mock_page.query_selector_all.assert_any_call(".group1")
    mock_page.query_selector_all.assert_any_call(".group2")


@pytest.mark.asyncio
async def test_get_text_with_string_selector(action_context, mock_page):
    """Test GetText action with a string selector"""
    mock_element = create_mock_element(text="Sample text content")
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    get_text = GetText(selector="#text-element")
    result = await get_text(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "Sample text content"
    mock_element.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_get_text_with_element_handle(action_context):
    """Test GetText action with an ElementHandle directly"""
    mock_element = create_mock_element(text="Direct element text")
    
    get_text = GetText(selector=mock_element)
    result = await get_text(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "Direct element text"
    mock_element.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_get_attribute(action_context, mock_page):
    """Test GetAttribute action"""
    mock_element = create_mock_element()
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    get_attribute = GetAttribute(selector="#attr-element", attribute="data-test")
    result = await get_attribute(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "value-of-data-test"
    mock_element.get_attribute.assert_called_once_with("data-test")


@pytest.mark.asyncio
async def test_get_html_with_outer_html(action_context, mock_page):
    """Test GetHtml action with outer HTML"""
    outer_html = "<div id='test'>Content</div>"
    mock_element = create_mock_element(html=outer_html)
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    get_html = GetHtml(selector="#html-element", outer=True)
    result = await get_html(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == outer_html
    mock_element.get_html.assert_called_once_with(outer=True)


@pytest.mark.asyncio
async def test_get_html_with_inner_html(action_context, mock_page):
    """Test GetHtml action with inner HTML"""
    inner_html = "Content"
    mock_element = create_mock_element()
    mock_element.get_html = AsyncMock(return_value=Ok(inner_html))
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    get_html = GetHtml(selector="#html-element", outer=False)
    result = await get_html(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == inner_html
    mock_element.get_html.assert_called_once_with(outer=False)


@pytest.mark.asyncio
async def test_get_inner_text(action_context, mock_page, mock_driver):
    """Test GetInnerText action"""
    mock_element = create_mock_element(selector="#inner-text-element")
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_driver.execute_script = AsyncMock(return_value=Ok("Visible inner text"))
    
    action_context.page = mock_page
    action_context.driver = mock_driver
    
    get_inner_text = GetInnerText(selector="#inner-text-element")
    result = await get_inner_text(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "Visible inner text"
    mock_driver.execute_script.assert_called_once()
    assert "#inner-text-element" in mock_driver.execute_script.call_args[0][1]


@pytest.mark.asyncio
async def test_wait_for_selector_with_string(action_context, mock_driver):
    """Test WaitForSelector action with string selector"""
    mock_driver.wait_for_selector = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    wait_for_selector = WaitForSelector(selector="#waiting-element")
    result = await wait_for_selector(context=action_context)
    
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("mock-page-id", "#waiting-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_options(action_context, mock_driver):
    """Test WaitForSelector action with wait options"""
    mock_driver.wait_for_selector = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    options = WaitOptions(timeout=5000, state="visible")
    
    wait_for_selector = WaitForSelector(selector="#waiting-element", options=options)
    result = await wait_for_selector(context=action_context)
    
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("mock-page-id", "#waiting-element", options)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_group(action_context, mock_driver):
    """Test WaitForSelector action with SelectorGroup"""
    mock_driver.execute_script = AsyncMock(return_value=Ok("element found"))
    
    action_context.driver = mock_driver
    
    selector1 = Selector(value="#element1", type="css")
    selector2 = Selector(value="#element2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    wait_for_selector = WaitForSelector(selector=selector_group)
    result = await wait_for_selector(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "element found"
    mock_driver.execute_script.assert_called_once()
    script = mock_driver.execute_script.call_args[0][1]
    assert "#element1" in script
    assert "#element2" in script


@pytest.mark.asyncio
async def test_element_exists_true(action_context, mock_page):
    """Test ElementExists action when element exists"""
    mock_element = create_mock_element()
    
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.page = mock_page
    
    element_exists = ElementExists(selector="#existing-element")
    result = await element_exists(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) is True


@pytest.mark.asyncio
async def test_element_exists_false(action_context, mock_page):
    """Test ElementExists action when element doesn't exist"""
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    action_context.page = mock_page
    
    element_exists = ElementExists(selector="#non-existing-element")
    result = await element_exists(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) is False


@pytest.mark.asyncio
async def test_query_no_page(action_context):
    """Test Query action when no page is available"""
    action_context.page = None
    
    query = Query(selector="#test-selector")
    result = await query(context=action_context)
    
    assert result.is_error()
    assert "No page found" in str(result.error)

@pytest.mark.asyncio
async def test_query_element_not_found(action_context, mock_page):
    """Test Query action when element is not found"""
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    action_context.page = mock_page
    query = Query(selector="#non-existent")
    result = await query(context=action_context)
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_get_text_element_not_found(action_context, mock_page):
    """Test GetText action when element is not found"""
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    action_context.page = mock_page
    get_text = GetText(selector="#non-existent")
    result = await get_text(context=action_context)
    assert result.is_ok()
    assert result.default_value("default") is None



@pytest.mark.asyncio
async def test_query_then_get_text_sequential(action_context, mock_page):
    """Test sequential operations: Query followed by GetText"""
    mock_element = create_mock_element(text="Sequential Text")
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    action_context.page = mock_page
    query = Query(selector="#sequential-element")
    query_result = await query(context=action_context)
    assert query_result.is_ok()
    element = query_result.default_value(None)
    get_text = GetText(selector=element)
    text_result = await get_text(context=action_context)
    assert text_result.is_ok()
    assert text_result.default_value(None) == "Sequential Text"


@pytest.mark.asyncio
async def test_complex_extraction_sequence(action_context, mock_page):
    """Test a complex sequence of extraction operations"""
    mock_form = create_mock_element("#login-form")
    mock_username = create_mock_element("#username", text="")
    mock_username.get_attribute = AsyncMock(return_value=Ok("username-field"))
    mock_password = create_mock_element("#password", text="")
    mock_button = create_mock_element("#submit-btn", text="Login")
    
    def mock_query_selector(selector):
        if selector == "#login-form":
            return Ok(mock_form)
        elif selector == "#username":
            return Ok(mock_username)
        elif selector == "#password":
            return Ok(mock_password)
        elif selector == "#submit-btn":
            return Ok(mock_button)
        return Ok(None)
    
    mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
    action_context.page = mock_page
    form_exists = ElementExists(selector="#login-form")
    form_exists_result = await form_exists(context=action_context)
    assert form_exists_result.is_ok()
    assert form_exists_result.default_value(None) is True
    get_username_attr = GetAttribute(selector="#username", attribute="name")
    attr_result = await get_username_attr(context=action_context)
    assert attr_result.is_ok()
    assert attr_result.default_value(None) == "username-field"
    get_button_text = GetText(selector="#submit-btn")
    text_result = await get_button_text(context=action_context)
    assert text_result.is_ok()
    assert text_result.default_value(None) == "Login"