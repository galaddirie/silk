"""
Tests for Silk input actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression import Error, Ok, Result

from silk.actions.input import (
    Click, DoubleClick, Drag, Fill, KeyPress, MouseDown, 
    MouseMove, MouseUp, Select, Type, Scroll
)
from silk.browsers.models import (
    ActionContext, 
    ElementHandle, 
    MouseOptions, 
    TypeOptions, 
    KeyModifier
)


def create_mock_element(selector="#test-selector"):
    """Create a mock element that implements ElementHandle protocol"""
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
    
    mock_element.get_bounding_box = AsyncMock(
        return_value=Ok({"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0})
    )
    
    return mock_element


@pytest.mark.asyncio
async def test_mouse_move_with_selector(action_context, mock_driver, mock_page):
    """Test MouseMove action with a selector"""
    mock_element = create_mock_element()
    
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    mouse_move = MouseMove(target="#test-selector")
    result = await mouse_move(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once_with("mock-page-id", 10.0, 20.0)


@pytest.mark.asyncio
async def test_mouse_move_with_coordinates(action_context, mock_driver):
    """Test MouseMove action with direct coordinates"""
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    mouse_move = MouseMove(target=(150, 250))
    result = await mouse_move(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once_with("mock-page-id", 150.0, 250.0)


@pytest.mark.asyncio
async def test_click_with_selector(action_context, mock_driver, mock_page):
    """Test Click action with a selector"""
    mock_element = create_mock_element("#test-selector")
    
    mock_driver.click = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    click = Click(target="#test-selector")
    result = await click(context=action_context)
    
    assert result.is_ok()
    mock_driver.click.assert_called_once_with("mock-page-id", "#test-selector", None)


@pytest.mark.asyncio
async def test_click_with_coordinates(action_context, mock_driver):
    """Test Click action with direct coordinates"""
    mock_driver.mouse_click = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    click = Click(target=(150, 250))
    result = await click(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_click.assert_called_once()


@pytest.mark.asyncio
async def test_double_click(action_context, mock_driver, mock_page):
    """Test DoubleClick action"""
    mock_element = create_mock_element("#test-selector")
    
    mock_driver.double_click = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    double_click = DoubleClick(target="#test-selector")
    result = await double_click(context=action_context)
    
    assert result.is_ok()
    mock_driver.double_click.assert_called_once_with("mock-page-id", "#test-selector", None)


@pytest.mark.asyncio
async def test_mouse_down(action_context, mock_driver):
    """Test MouseDown action"""
    mock_driver.mouse_down = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    mouse_down = MouseDown()
    result = await mouse_down(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_down.assert_called_once_with("mock-page-id", "left", None)


@pytest.mark.asyncio
async def test_mouse_up(action_context, mock_driver):
    """Test MouseUp action"""
    mock_driver.mouse_up = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    mouse_up = MouseUp()
    result = await mouse_up(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_up.assert_called_once_with("mock-page-id", "left", None)


@pytest.mark.asyncio
async def test_drag(action_context, mock_driver, mock_page):
    """Test Drag action between two elements"""
    source_element = create_mock_element("#source")
    target_element = create_mock_element("#target")
    target_element.get_bounding_box = AsyncMock(
        return_value=Ok({"x": 100.0, "y": 200.0, "width": 100.0, "height": 50.0})
    )
    
    mock_driver.mouse_drag = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock()
    mock_page.query_selector.side_effect = [
        Ok(source_element),
        Ok(target_element)
    ]
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    drag = Drag(source="#source", target="#target")
    result = await drag(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_drag.assert_called_once_with(
        "mock-page-id", (10, 20), (100, 200), None
    )


@pytest.mark.asyncio
async def test_fill(action_context, mock_driver, mock_page):
    """Test Fill action"""
    mock_element = create_mock_element("#input-field")
    
    mock_driver.fill = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    fill = Fill(target="#input-field", text="test text")
    result = await fill(context=action_context)
    
    assert result.is_ok()
    mock_driver.fill.assert_called_once_with(
        "mock-page-id", "#input-field", "test text", None
    )


@pytest.mark.asyncio
async def test_type(action_context, mock_driver, mock_page):
    """Test Type action"""
    mock_element = create_mock_element("#input-field")
    
    mock_driver.type = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    type_action = Type(target="#input-field", text="test text")
    result = await type_action(context=action_context)
    
    assert result.is_ok()
    mock_driver.type.assert_called_once_with(
        "mock-page-id", "#input-field", "test text", None
    )


@pytest.mark.asyncio
async def test_key_press(action_context, mock_driver):
    """Test KeyPress action"""
    mock_driver.key_press = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    key_press = KeyPress(key="Enter")
    result = await key_press(context=action_context)
    
    assert result.is_ok()
    mock_driver.key_press.assert_called_once_with("mock-page-id", "Enter", None)


@pytest.mark.asyncio
async def test_key_press_with_modifiers(action_context, mock_driver):
    """Test KeyPress action with modifiers"""
    mock_driver.key_press = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    key_press = KeyPress(key="a", modifiers=[KeyModifier.CTRL])
    result = await key_press(context=action_context)
    
    assert result.is_ok()
    mock_driver.key_press.assert_called_once()
    args, kwargs = mock_driver.key_press.call_args
    assert "mock-page-id" == args[0]
    assert "a" == args[1]
    assert hasattr(args[2], 'modifiers')
    assert args[2].modifiers == [KeyModifier.CTRL]


@pytest.mark.asyncio
async def test_select(action_context, mock_driver, mock_page):
    """Test Select action"""
    mock_element = create_mock_element("#dropdown")
    
    mock_driver.select = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    select = Select(target="#dropdown", value="option1")
    result = await select(context=action_context)
    
    assert result.is_ok()
    mock_driver.select.assert_called_once_with(
        "mock-page-id", "#dropdown", "option1", None
    )


@pytest.mark.asyncio
async def test_select_by_text(action_context, mock_driver, mock_page):
    """Test Select action using text instead of value"""
    mock_element = create_mock_element("#dropdown")
    
    mock_driver.select = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    select = Select(target="#dropdown", text="Option 1")
    result = await select(context=action_context)
    
    assert result.is_ok()
    mock_driver.select.assert_called_once_with(
        "mock-page-id", "#dropdown", None, "Option 1"
    )


@pytest.mark.asyncio
async def test_scroll_to_coordinates(action_context, mock_driver):
    """Test Scroll action with coordinates"""
    mock_driver.scroll = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    scroll = Scroll(x=100, y=200)
    result = await scroll(context=action_context)
    
    assert result.is_ok()
    mock_driver.scroll.assert_called_once_with("mock-page-id", x=100, y=200)


@pytest.mark.asyncio
async def test_scroll_to_element(action_context, mock_driver, mock_page):
    """Test Scroll action with element selector"""
    mock_element = create_mock_element("#test-element")
    
    mock_driver.scroll = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    scroll = Scroll(target="#test-element")
    result = await scroll(context=action_context)
    
    assert result.is_ok()
    mock_driver.scroll.assert_called_once_with("mock-page-id", selector="#test-element")


@pytest.mark.asyncio
async def test_scroll_with_tuple_coordinates(action_context, mock_driver):
    """Test Scroll action with coordinate tuple"""
    mock_driver.scroll = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    
    scroll = Scroll(target=(150, 250))
    result = await scroll(context=action_context)
    
    assert result.is_ok()
    mock_driver.scroll.assert_called_once_with("mock-page-id", x=150, y=250)


@pytest.mark.asyncio
async def test_click_with_no_driver(action_context):
    """Test Click action when no driver is available"""
    action_context.driver = None
    
    click = Click(target="#test-selector")
    result = await click(context=action_context)
    
    assert result.is_error()
    assert "No driver found" in str(result.error)


@pytest.mark.asyncio
async def test_click_with_no_element(action_context, mock_driver, mock_page):
    """Test Click action when element is not found"""
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    click = Click(target="#non-existent")
    result = await click(context=action_context)
    
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_drag_with_source_not_found(action_context, mock_driver, mock_page):
    """Test Drag action when source element is not found"""
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    drag = Drag(source="#source", target="#target")
    result = await drag(context=action_context)
    
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_scroll_error_no_target(action_context, mock_driver):
    """Test Scroll action with no target or coordinates"""
    action_context.driver = mock_driver
    
    scroll = Scroll()
    result = await scroll(context=action_context)
    
    assert result.is_error()
    assert "Either target or scroll coordinates" in str(result.error)


@pytest.mark.asyncio
async def test_fill_then_click_sequential_composition(action_context, mock_driver, mock_page):
    """Test sequential composition with fill followed by click"""
    input_element = create_mock_element("#input-field")
    button_element = create_mock_element("#submit-button")
    
    mock_driver.fill = AsyncMock(return_value=Ok(None))
    mock_driver.click = AsyncMock(return_value=Ok(None))
    
    def mock_query_selector(selector):
        if selector == "#input-field":
            return Ok(input_element)
        elif selector == "#submit-button":
            return Ok(button_element)
        return Ok(None)
    
    mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    fill = Fill(target="#input-field", text="test text")
    fill_result = await fill(context=action_context)
    assert fill_result.is_ok()
    
    click = Click(target="#submit-button")
    click_result = await click(context=action_context)
    assert click_result.is_ok()
    
    mock_driver.fill.assert_called_once_with(
        "mock-page-id", "#input-field", "test text", None
    )
    mock_driver.click.assert_called_once_with(
        "mock-page-id", "#submit-button", None
    )


@pytest.mark.asyncio
async def test_mouse_move_with_element_handle(action_context, mock_driver, mock_page):
    """Test MouseMove with ElementHandle passed directly"""
    mock_element = create_mock_element()
    
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    mouse_move = MouseMove(target=mock_element)
    result = await mouse_move(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once_with("mock-page-id", 10.0, 20.0)


@pytest.mark.asyncio
async def test_drag_with_element_handles(action_context, mock_driver, mock_page):
    """Test Drag with ElementHandle objects"""
    source_element = create_mock_element("#source")
    target_element = create_mock_element("#target")
    target_element.get_bounding_box = AsyncMock(
        return_value=Ok({"x": 100.0, "y": 200.0, "width": 100.0, "height": 50.0})
    )
    
    mock_driver.mouse_drag = AsyncMock(return_value=Ok(None))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    drag = Drag(source=source_element, target=target_element)
    result = await drag(context=action_context)
    
    assert result.is_ok()
    mock_driver.mouse_drag.assert_called_once_with(
        "mock-page-id", (10, 20), (100, 200), None
    )


@pytest.mark.asyncio
async def test_click_with_mouse_options(action_context, mock_driver, mock_page, mock_mouse_options):
    """Test Click action with MouseOptions"""
    mock_element = create_mock_element("#test-selector")
    
    mock_driver.click = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    click = Click(target="#test-selector", options=mock_mouse_options)
    result = await click(context=action_context)
    
    assert result.is_ok()
    mock_driver.click.assert_called_once_with("mock-page-id", "#test-selector", mock_mouse_options)


@pytest.mark.asyncio
async def test_fill_with_type_options(action_context, mock_driver, mock_page, mock_type_options):
    """Test Fill action with TypeOptions"""
    mock_element = create_mock_element("#input-field")
    
    mock_driver.fill = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    action_context.driver = mock_driver
    action_context.page = mock_page
    
    fill = Fill(target="#input-field", text="test text", options=mock_type_options)
    result = await fill(context=action_context)
    
    assert result.is_ok()
    mock_driver.fill.assert_called_once_with(
        "mock-page-id", "#input-field", "test text", mock_type_options
    )