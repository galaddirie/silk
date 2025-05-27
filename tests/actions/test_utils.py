"""
Tests for utils functions in the Silk actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression import Error, Ok, Result

from silk.browsers.models import ActionContext, ElementHandle
from silk.actions.utils import (
    resolve_target, validate_driver, get_element_coordinates
)
from silk.selectors.selector import Selector, SelectorGroup, css


@pytest.mark.asyncio
async def test_resolve_target_with_string(action_context: ActionContext):
    """Test resolve_target with a string selector"""
    mock_element = MagicMock(spec=ElementHandle)
    
    action_context.page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    result = await resolve_target(action_context, "#test-selector")
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    action_context.page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_resolve_target_with_selector(action_context: ActionContext):
    """Test resolve_target with a Selector object"""
    mock_element = MagicMock(spec=ElementHandle)
    selector = css("#test-selector")
    
    action_context.page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    result = await resolve_target(action_context, selector)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    action_context.page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_resolve_target_with_selector_group(action_context: ActionContext):
    """Test resolve_target with a SelectorGroup object"""
    mock_element = MagicMock(spec=ElementHandle)
    
    selector_group = SelectorGroup(
        "test_group",
        css("#selector1"),
        css("#selector2")
    )
    
    action_context.page.query_selector = AsyncMock()
    action_context.page.query_selector.side_effect = [
        Error(Exception("Not found")),
        Ok(mock_element)
    ]
    
    result = await resolve_target(action_context, selector_group)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element
    assert action_context.page.query_selector.call_count == 2


@pytest.mark.asyncio
async def test_resolve_target_with_element_handle(action_context: ActionContext, mock_element_handle: ElementHandle):
    """Test resolve_target with an ElementHandle directly"""
    result = await resolve_target(action_context, mock_element_handle)
    
    assert result.is_ok()
    assert result.default_value(None) == mock_element_handle


@pytest.mark.asyncio
async def test_resolve_target_with_no_page(action_context: ActionContext):
    """Test resolve_target when no page is available"""
    action_context.page = None
    
    result = await resolve_target(action_context, "#test-selector")
    
    assert result.is_error()
    assert "No page found" in str(result.error)


@pytest.mark.asyncio
async def test_resolve_target_with_no_element(action_context: ActionContext):
    """Test resolve_target when no element is found"""
    action_context.page.query_selector = AsyncMock(return_value=Ok(None))
    
    result = await resolve_target(action_context, "#non-existent")
    
    assert result.is_error()
    assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_resolve_target_with_unsupported_type(action_context: ActionContext):
    """Test resolve_target with an unsupported target type"""
    result = await resolve_target(action_context, 123)
    
    assert result.is_error()
    assert "Unsupported target type" in str(result.error)


@pytest.mark.asyncio
async def test_validate_driver_success(action_context: ActionContext):
    """Test validate_driver with valid driver and page_id"""
    result = await validate_driver(action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == action_context.driver


@pytest.mark.asyncio
async def test_validate_driver_no_driver(action_context: ActionContext):
    """Test validate_driver when no driver is available"""
    action_context.driver = None
    
    result = await validate_driver(action_context)
    
    assert result.is_error()
    assert "No driver found" in str(result.error)


@pytest.mark.asyncio
async def test_validate_driver_no_page_id(action_context: ActionContext):
    """Test validate_driver when no page_id is set"""
    action_context.page_id = None
    
    result = await validate_driver(action_context)
    
    assert result.is_error()
    assert "No page found" in str(result.error)


@pytest.mark.asyncio
async def test_get_element_coordinates_from_tuple():
    """Test get_element_coordinates with coordinate tuple"""
    result = await get_element_coordinates((100, 200))
    
    assert result.is_ok()
    x, y = result.default_value((0.0, 0.0))
    assert x == 100.0
    assert y == 200.0


@pytest.mark.asyncio
async def test_get_element_coordinates_from_element(mock_element_handle: ElementHandle):
    """Test get_element_coordinates with element handle"""
    mock_element_handle.get_bounding_box = AsyncMock(return_value=Ok({"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0}))
    
    result = await get_element_coordinates(mock_element_handle)
    
    assert result.is_ok()
    x, y = result.default_value((0.0, 0.0))
    assert x == 10.0
    assert y == 20.0


@pytest.mark.asyncio
async def test_get_element_coordinates_from_element_with_center(mock_element_handle: ElementHandle):
    """Test get_element_coordinates with element handle and center option"""
    mock_element_handle.get_bounding_box = AsyncMock(return_value=Ok({"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0}))
    
    options = MagicMock()
    options.move_to_center = True
    options.timeout = None 
    
    result = await get_element_coordinates(mock_element_handle, options)
    
    assert result.is_ok()
    x, y = result.default_value((0.0, 0.0))
    assert x == 60.0
    assert y == 45.0


@pytest.mark.asyncio
async def test_get_element_coordinates_with_error(mock_element_handle: ElementHandle):
    """Test get_element_coordinates when bounding box cannot be retrieved"""
    mock_element_handle.get_bounding_box = AsyncMock(return_value=Error(Exception("Bounding box error")))
    
    result = await get_element_coordinates(mock_element_handle)
    
    assert result.is_error()
    assert "Bounding box error" in str(result.error)