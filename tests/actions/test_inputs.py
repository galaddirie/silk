"""
Tests for Silk input actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression.core import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.input import (
    Click, DoubleClick, Drag, Fill, KeyPress, MouseDown, 
    MouseMove, MouseUp, Select, Type
)
from silk.browsers.element import ElementHandle
from silk.browsers.types import MouseOptions, TypeOptions, KeyModifier


# -------------------- Helper Functions for Testing --------------------

async def create_test_action_context(mock_driver=None, mock_page=None):
    """Create a context with mocked driver and page for testing actions"""
    context = MagicMock(spec=ActionContext)
    context.page_id = "test-page-id"
    
    if mock_driver:
        context.get_driver = AsyncMock(return_value=Ok(mock_driver))
    
    if mock_page:
        context.get_page = AsyncMock(return_value=Ok(mock_page))
    
    return context


# -------------------- Input Action Tests --------------------

@pytest.mark.asyncio
async def test_mouse_move_with_selector():
    """Test MouseMove action with a selector"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_bounding_box = AsyncMock(return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50}))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    mouse_move = MouseMove(target="#test-selector")
    result = await mouse_move(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once_with("test-page-id", 10.0, 20.0)


@pytest.mark.asyncio
async def test_mouse_move_with_coordinates():
    """Test MouseMove action with direct coordinates"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    mouse_move = MouseMove(target=(150, 250))
    result = await mouse_move(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once_with("test-page-id", 150.0, 250.0)


@pytest.mark.asyncio
async def test_click_with_selector():
    """Test Click action with a selector"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.click = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#test-selector")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    click = Click(target="#test-selector")
    result = await click(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.click.assert_called_once_with("test-page-id", "#test-selector", None)


@pytest.mark.asyncio
async def test_click_with_coordinates():
    """Test Click action with direct coordinates"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.mouse_move = AsyncMock(return_value=Ok(None))
    mock_driver.mouse_click = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    click = Click(target=(150, 250))
    result = await click(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_move.assert_called_once()
    mock_driver.mouse_click.assert_called_once()


@pytest.mark.asyncio
async def test_double_click():
    """Test DoubleClick action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.double_click = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#test-selector")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    double_click = DoubleClick(target="#test-selector")
    result = await double_click(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.double_click.assert_called_once_with("test-page-id", "#test-selector", None)


@pytest.mark.asyncio
async def test_mouse_down():
    """Test MouseDown action"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.mouse_down = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    mouse_down = MouseDown()
    result = await mouse_down(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_down.assert_called_once_with("test-page-id", "left", None)


@pytest.mark.asyncio
async def test_mouse_up():
    """Test MouseUp action"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.mouse_up = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    mouse_up = MouseUp()
    result = await mouse_up(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_up.assert_called_once_with("test-page-id", "left", None)


@pytest.mark.asyncio
async def test_drag():
    """Test Drag action between two elements"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    source_element = MagicMock(spec=ElementHandle)
    target_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.mouse_drag = AsyncMock(return_value=Ok(None))
    # Prepare query_selector to return different elements
    mock_page.query_selector = AsyncMock()
    mock_page.query_selector.side_effect = [
        Ok(source_element),
        Ok(target_element)
    ]
    
    # Configure elements
    source_element.get_bounding_box = AsyncMock(return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50}))
    target_element.get_bounding_box = AsyncMock(return_value=Ok({"x": 100, "y": 200, "width": 100, "height": 50}))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    drag = Drag(source="#source", target="#target")
    result = await drag(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.mouse_drag.assert_called_once_with(
        "test-page-id", (10, 20), (100, 200), None
    )


@pytest.mark.asyncio
async def test_fill():
    """Test Fill action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.fill = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#input-field")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    fill = Fill(target="#input-field", text="test text")
    result = await fill(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.fill.assert_called_once_with(
        "test-page-id", "#input-field", "test text", None
    )


@pytest.mark.asyncio
async def test_type():
    """Test Type action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.type = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#input-field")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    type_action = Type(target="#input-field", text="test text")
    result = await type_action(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.type.assert_called_once_with(
        "test-page-id", "#input-field", "test text", None
    )


@pytest.mark.asyncio
async def test_key_press():
    """Test KeyPress action"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.key_press = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    key_press = KeyPress(key="Enter")
    result = await key_press(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.key_press.assert_called_once_with("test-page-id", "Enter", None)


@pytest.mark.asyncio
async def test_key_press_with_modifiers():
    """Test KeyPress action with modifiers"""
    # Setup mocks
    mock_driver = MagicMock()
    
    # Configure mocks
    mock_driver.key_press = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked driver
    context = await create_test_action_context(mock_driver)
    
    # Execute
    key_press = KeyPress(key="a", modifiers=[KeyModifier.CTRL])
    result = await key_press(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.key_press.assert_called_once()
    # Check that the TypeOptions with modifiers was passed
    args, kwargs = mock_driver.key_press.call_args
    assert "test-page-id" == args[0]
    assert "a" == args[1]
    assert hasattr(args[2], 'modifiers')
    assert args[2].modifiers == [KeyModifier.CTRL]


@pytest.mark.asyncio
async def test_select():
    """Test Select action"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.select = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#dropdown")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    select = Select(target="#dropdown", value="option1")
    result = await select(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.select.assert_called_once_with(
        "test-page-id", "#dropdown", "option1", None
    )


@pytest.mark.asyncio
async def test_select_by_text():
    """Test Select action using text instead of value"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.select = AsyncMock(return_value=Ok(None))
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    mock_element.get_selector = MagicMock(return_value="#dropdown")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    select = Select(target="#dropdown", text="Option 1")
    result = await select(context=context)
    
    # Assert
    assert result.is_ok()
    mock_driver.select.assert_called_once_with(
        "test-page-id", "#dropdown", None, "Option 1"
    )


# -------------------- Error Case Tests --------------------

@pytest.mark.asyncio
async def test_click_with_no_driver():
    """Test Click action when no driver is available"""
    # Create context with no driver method that returns an error
    context = MagicMock(spec=ActionContext)
    context.page_id = "test-page-id"
    context.get_driver = AsyncMock(return_value=Error(Exception("No driver")))
    
    # Execute
    click = Click(target="#test-selector")
    result = await click(context=context)
    
    # Assert
    assert result.is_error()
    assert "No driver" in str(result.error)


@pytest.mark.asyncio
async def test_click_with_no_element():
    """Test Click action when element is not found"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - no element found
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    click = Click(target="#non-existent")
    result = await click(context=context)
    
    # Assert
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_drag_with_source_not_found():
    """Test Drag action when source element is not found"""
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    
    # Configure mocks - no source element found
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute
    drag = Drag(source="#source", target="#target")
    result = await drag(context=context)
    
    # Assert
    assert result.is_error()
    assert "No element found" in str(result.error)


# -------------------- Sequential Composition Tests --------------------

@pytest.mark.asyncio
async def test_fill_then_click_sequential_composition():
    """Test sequential composition with fill followed by click"""
    # This test will just verify that we can call them in sequence,
    # since we can't properly test >> composition in isolation
    
    # Setup mocks
    mock_driver = MagicMock()
    mock_page = MagicMock()
    input_element = MagicMock(spec=ElementHandle)
    button_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_driver.fill = AsyncMock(return_value=Ok(None))
    mock_driver.click = AsyncMock(return_value=Ok(None))
    
    # Set up query_selector to return different elements
    def mock_query_selector(selector):
        if selector == "#input-field":
            return Ok(input_element)
        elif selector == "#submit-button":
            return Ok(button_element)
        return Ok(None)
    
    mock_page.query_selector = AsyncMock(side_effect=mock_query_selector)
    
    # Configure elements
    input_element.get_selector = MagicMock(return_value="#input-field")
    button_element.get_selector = MagicMock(return_value="#submit-button")
    
    # Create context with mocked methods
    context = await create_test_action_context(mock_driver, mock_page)
    
    # Execute fill operation
    fill = Fill(target="#input-field", text="test text")
    fill_result = await fill(context=context)
    assert fill_result.is_ok()
    
    # Execute click operation
    click = Click(target="#submit-button")
    click_result = await click(context=context)
    assert click_result.is_ok()
    
    # Verify both actions were called correctly
    mock_driver.fill.assert_called_once_with(
        "test-page-id", "#input-field", "test text", None
    )
    mock_driver.click.assert_called_once_with(
        "test-page-id", "#submit-button", None
    )