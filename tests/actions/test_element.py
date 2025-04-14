"""
Tests for Silk extraction actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression.core import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.elements import (
    Query, QueryAll, GetText, GetAttribute, GetHtml, 
    GetInnerText, ExtractTable, WaitForSelector, ElementExists
)
from silk.browsers.element import ElementHandle
from silk.browsers.types import WaitOptions
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
    else:
        # Default implementation if no mock_page provided
        context.get_page = AsyncMock(return_value=Error(Exception("No page provided")))
    
    return context


def create_mock_element(selector="#test-selector", text="Test Text", html="<div>Test Text</div>"):
    """Create a mock element with common methods"""
    mock_element = MagicMock(spec=ElementHandle)
    mock_element.get_selector = MagicMock(return_value=selector)
    mock_element.get_text = AsyncMock(return_value=Ok(text))
    mock_element.get_html = AsyncMock(return_value=Ok(html))
    mock_element.get_attribute = AsyncMock(side_effect=lambda attr: Ok(f"value-of-{attr}"))
    mock_element.query_selector_all = AsyncMock(return_value=Ok([]))
    return mock_element


# -------------------- Extraction Action Tests --------------------

@pytest.mark.asyncio
async def test_query_with_string_selector():
    """Test Query action with a string selector"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element()
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    query = Query(selector="#test-selector")
    result = await query(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_query_with_selector_object():
    """Test Query action with a Selector object"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element()
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Create selector object
    selector = Selector(value="#test-selector", type="css")
    
    # Execute
    query = Query(selector=selector)
    result = await query(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_query_with_selector_group():
    """Test Query action with a SelectorGroup object"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element()
    
    # Configure mocks - first selector succeeds
    mock_page.query_selector = AsyncMock()
    mock_page.query_selector.side_effect = [
        Ok(mock_element),  # First selector finds element
        Ok(None)           # Second selector would not find element (not called)
    ]
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Create selector group
    selector1 = Selector(value="#element1", type="css")
    selector2 = Selector(value="#element2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    # Execute
    query = Query(selector=selector_group)
    result = await query(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    # Only first selector should be tried since it succeeds
    mock_page.query_selector.assert_called_once_with("#element1")


@pytest.mark.asyncio
async def test_query_all_with_string_selector():
    """Test QueryAll action with a string selector"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element1 = create_mock_element("#element1", "Text 1")
    mock_element2 = create_mock_element("#element2", "Text 2")
    
    # Configure mocks
    mock_page.query_selector_all = AsyncMock(return_value=Ok([mock_element1, mock_element2]))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    query_all = QueryAll(selector=".test-elements")
    result = await query_all(context=context)
    
    # Assert
    assert result.is_ok()
    elements = result.default_value(None)
    assert len(elements) == 2
    assert elements[0] == mock_element1
    assert elements[1] == mock_element2
    mock_page.query_selector_all.assert_called_once_with(".test-elements")


@pytest.mark.asyncio
async def test_query_all_with_selector_group():
    """Test QueryAll action with a SelectorGroup object"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element1 = create_mock_element("#element1", "Text 1")
    mock_element2 = create_mock_element("#element2", "Text 2")
    mock_element3 = create_mock_element("#element3", "Text 3")
    
    # Configure mocks
    mock_page.query_selector_all = AsyncMock()
    mock_page.query_selector_all.side_effect = [
        Ok([mock_element1]),           # Results from first selector
        Ok([mock_element2, mock_element3])  # Results from second selector
    ]
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Create selector group
    selector1 = Selector(value=".group1", type="css")
    selector2 = Selector(value=".group2", type="css")
    selector_group = SelectorGroup("group", selector1, selector2)
    
    # Execute
    query_all = QueryAll(selector=selector_group)
    result = await query_all(context=context)
    
    # Assert
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
async def test_get_text_with_string_selector():
    """Test GetText action with a string selector"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element(text="Sample text content")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_text = GetText(selector="#text-element")
    result = await get_text(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "Sample text content"
    mock_element.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_get_text_with_element_handle():
    """Test GetText action with an ElementHandle directly"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_element = create_mock_element(text="Direct element text")
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    get_text = GetText(selector=mock_element)
    result = await get_text(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "Direct element text"
    mock_element.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_get_attribute():
    """Test GetAttribute action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element()
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_attribute = GetAttribute(selector="#attr-element", attribute="data-test")
    result = await get_attribute(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "value-of-data-test"
    mock_element.get_attribute.assert_called_once_with("data-test")


@pytest.mark.asyncio
async def test_get_html_with_outer_html():
    """Test GetHtml action with outer HTML"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    outer_html = "<div id='test'>Content</div>"
    mock_element = create_mock_element(html=outer_html)
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_html = GetHtml(selector="#html-element", outer=True)
    result = await get_html(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == outer_html
    mock_element.get_html.assert_called_once_with(outer=True)


@pytest.mark.asyncio
async def test_get_html_with_inner_html():
    """Test GetHtml action with inner HTML"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    inner_html = "Content"
    mock_element = create_mock_element()
    mock_element.get_html = AsyncMock(return_value=Ok(inner_html))
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_html = GetHtml(selector="#html-element", outer=False)
    result = await get_html(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == inner_html
    mock_element.get_html.assert_called_once_with(outer=False)


@pytest.mark.asyncio
async def test_get_inner_text():
    """Test GetInnerText action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element(selector="#inner-text-element")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_driver.execute_script = AsyncMock(return_value=Ok("Visible inner text"))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_inner_text = GetInnerText(selector="#inner-text-element")
    result = await get_inner_text(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "Visible inner text"
    mock_driver.execute_script.assert_called_once()
    # Check that we're calling with the right selector
    assert "#inner-text-element" in mock_driver.execute_script.call_args[0][1]


@pytest.mark.asyncio
async def test_extract_table_with_headers():
    """Test ExtractTable action with headers"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_table = create_mock_element(selector="table")
    
    # Create header elements
    header1 = create_mock_element(text="Name")
    header2 = create_mock_element(text="Age")
    
    # Create row elements
    row1 = create_mock_element()
    row2 = create_mock_element()
    
    # Create cell elements
    cell1 = create_mock_element(text="John")
    cell2 = create_mock_element(text="30")
    cell3 = create_mock_element(text="Alice")
    cell4 = create_mock_element(text="25")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_table))
    mock_page.query_selector_all = AsyncMock()
    mock_page.query_selector_all.side_effect = [
        Ok([header1, header2]),  # Table headers
        Ok([row1, row2])         # Table rows
    ]
    
    # Configure row elements to return cells
    row1.query_selector_all = AsyncMock(return_value=Ok([cell1, cell2]))
    row2.query_selector_all = AsyncMock(return_value=Ok([cell3, cell4]))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    extract_table = ExtractTable(table_selector="table", include_headers=True)
    result = await extract_table(context=context)
    
    # Assert
    assert result.is_ok()
    table_data = result.default_value(None)
    assert len(table_data) == 2
    assert table_data[0] == {"Name": "John", "Age": "30"}
    assert table_data[1] == {"Name": "Alice", "Age": "25"}


@pytest.mark.asyncio
async def test_extract_table_without_headers():
    """Test ExtractTable action without headers"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_table = create_mock_element(selector="table")
    
    # Create row elements
    row1 = create_mock_element()
    row2 = create_mock_element()
    
    # Create cell elements
    cell1 = create_mock_element(text="John")
    cell2 = create_mock_element(text="30")
    cell3 = create_mock_element(text="Alice")
    cell4 = create_mock_element(text="25")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_table))
    mock_page.query_selector_all = AsyncMock(return_value=Ok([row1, row2]))
    
    # Configure row elements to return cells
    row1.query_selector_all = AsyncMock(return_value=Ok([cell1, cell2]))
    row2.query_selector_all = AsyncMock(return_value=Ok([cell3, cell4]))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    extract_table = ExtractTable(table_selector="table", include_headers=False)
    result = await extract_table(context=context)
    
    # Assert
    assert result.is_ok()
    table_data = result.default_value(None)
    assert len(table_data) == 2
    assert table_data[0] == {"column_0": "John", "column_1": "30"}
    assert table_data[1] == {"column_0": "Alice", "column_1": "25"}


@pytest.mark.asyncio
async def test_extract_table_with_custom_selectors():
    """Test ExtractTable action with custom selectors"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_table = create_mock_element(selector=".custom-table")
    
    # Create header elements
    header1 = create_mock_element(text="Column1")
    header2 = create_mock_element(text="Column2")
    
    # Create row elements
    row1 = create_mock_element()
    
    # Create cell elements
    cell1 = create_mock_element(text="Value1")
    cell2 = create_mock_element(text="Value2")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_table))
    mock_page.query_selector_all = AsyncMock()
    mock_page.query_selector_all.side_effect = [
        Ok([header1, header2]),  # Custom header selector results
        Ok([row1])               # Custom row selector results
    ]
    
    # Configure row element to return cells
    row1.query_selector_all = AsyncMock(return_value=Ok([cell1, cell2]))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute with custom selectors
    extract_table = ExtractTable(
        table_selector=".custom-table",
        header_selector=".custom-header",
        row_selector=".custom-row",
        cell_selector=".custom-cell"
    )
    result = await extract_table(context=context)
    
    # Assert
    assert result.is_ok()
    table_data = result.default_value(None)
    assert len(table_data) == 1
    assert table_data[0] == {"Column1": "Value1", "Column2": "Value2"}
    
    # Verify custom selectors were used
    mock_page.query_selector_all.assert_any_call(".custom-table .custom-header")
    mock_page.query_selector_all.assert_any_call(".custom-table .custom-row")
    row1.query_selector_all.assert_called_with(".custom-cell")


@pytest.mark.asyncio
async def test_wait_for_selector_with_string():
    """Test WaitForSelector action with string selector"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    wait_for_selector = WaitForSelector(selector="#waiting-element")
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#waiting-element", None)


@pytest.mark.asyncio
async def test_wait_for_selector_with_options():
    """Test WaitForSelector action with wait options"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.wait_for_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Create wait options
    options = WaitOptions(timeout=5000, visible=True)
    
    # Execute
    wait_for_selector = WaitForSelector(selector="#waiting-element", options=options)
    result = await wait_for_selector(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.wait_for_selector.assert_called_once_with("test-page-id", "#waiting-element", options)


@pytest.mark.asyncio
async def test_wait_for_selector_with_selector_group():
    """Test WaitForSelector action with SelectorGroup"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks - for selector groups, execute_script is used
    mock_driver.execute_script = AsyncMock(return_value=Ok("element found"))
    
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
    assert result.default_value(None) == "element found"
    mock_driver.execute_script.assert_called_once()
    # Check that both selectors are in the script
    script = mock_driver.execute_script.call_args[0][1]
    assert "#element1" in script
    assert "#element2" in script


@pytest.mark.asyncio
async def test_element_exists_true():
    """Test ElementExists action when element exists"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element()
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    element_exists = ElementExists(selector="#existing-element")
    result = await element_exists(context=context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) is True


@pytest.mark.asyncio
async def test_element_exists_false():
    """Test ElementExists action when element doesn't exist"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - Element not found
    mock_page.query_selector = AsyncMock(return_value=Error(Exception("No element found")))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    element_exists = ElementExists(selector="#non-existing-element")
    result = await element_exists(context=context)
    
    # Assert
    assert result.is_error()


# -------------------- Error Case Tests --------------------

@pytest.mark.asyncio
async def test_query_no_page():
    """Test Query action when no page is available"""
    # Create context with no page
    context = await create_test_action_context(MagicMock())
    
    # Execute
    query = Query(selector="#test-selector")
    result = await query(context=context)
    
    # Assert
    assert result.is_error()
    assert "No page provided" in str(result.error)


@pytest.mark.asyncio
async def test_query_element_not_found():
    """Test Query action when element is not found"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - No element found
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    query = Query(selector="#non-existent")
    result = await query(context=context)
    
    # Assert
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_get_text_element_not_found():
    """Test GetText action when element is not found"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - No element found
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    get_text = GetText(selector="#non-existent")
    result = await get_text(context=context)
    
    # Assert
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_extract_table_no_table_found():
    """Test ExtractTable action when table element is not found"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - No table found
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    extract_table = ExtractTable(table_selector="#non-existent-table")
    result = await extract_table(context=context)
    
    # Assert
    assert result.is_error()
    assert "No element found" in str(result.error)


# -------------------- Integration Tests (Sequential Actions) --------------------

@pytest.mark.asyncio
async def test_query_then_get_text_sequential():
    """Test sequential operations: Query followed by GetText"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = create_mock_element(text="Sequential Text")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute Query operation
    query = Query(selector="#sequential-element")
    query_result = await query(context=context)
    assert query_result.is_ok()
    
    # Get the element from query result
    element = query_result.default_value(None)
    
    # Execute GetText with the element
    get_text = GetText(selector=element)
    text_result = await get_text(context=context)
    
    # Assert
    assert text_result.is_ok()
    assert text_result.default_value(None) == "Sequential Text"


@pytest.mark.asyncio
async def test_complex_extraction_sequence():
    """Test a complex sequence of extraction operations"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_form = create_mock_element("#login-form")
    mock_username = create_mock_element("#username", text="")
    mock_username.get_attribute = AsyncMock(return_value=Ok("username-field"))
    mock_password = create_mock_element("#password", text="")
    mock_button = create_mock_element("#submit-btn", text="Login")
    
    # Configure mocks for different selectors
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
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # 1. Check if form exists
    form_exists = ElementExists(selector="#login-form")
    form_exists_result = await form_exists(context=context)
    assert form_exists_result.is_ok()
    assert form_exists_result.default_value(None) is True
    
    # 2. Get username field and its attribute
    get_username_attr = GetAttribute(selector="#username", attribute="name")
    attr_result = await get_username_attr(context=context)
    assert attr_result.is_ok()
    assert attr_result.default_value(None) == "username-field"
    
    # 3. Get button text
    get_button_text = GetText(selector="#submit-btn")
    text_result = await get_button_text(context=context)
    
    # Assert final result
    assert text_result.is_ok()
    assert text_result.default_value(None) == "Login"