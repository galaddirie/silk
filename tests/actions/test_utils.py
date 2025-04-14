"""
Tests for utils functions in the Silk actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.utils import (
    resolve_target, validate_driver, get_element_coordinates
)
from silk.browsers.element import ElementHandle
from silk.browsers.manager import BrowserManager  # Add this import
from silk.selectors.selector import Selector, SelectorGroup, css


@pytest.mark.asyncio
async def test_resolve_target_with_string():
    """Test resolve_target with a string selector"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch the get_page method
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Execute
        result = await resolve_target(context, "#test-selector")
        
        # Assert
        assert result.is_ok()
        assert result.default_value(None) == mock_element
        mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_resolve_target_with_selector():
    """Test resolve_target with a Selector object"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    selector = css("#test-selector")
    
    # Configure mocks
    mock_page.query_selector = AsyncMock(return_value=Ok(mock_element))
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch the get_page method
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Execute
        result = await resolve_target(context, selector)
        
        # Assert
        assert result.is_ok()
        assert result.default_value(None) == mock_element
        mock_page.query_selector.assert_called_once_with("#test-selector")


@pytest.mark.asyncio
async def test_resolve_target_with_selector_group():
    """Test resolve_target with a SelectorGroup object"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_page = MagicMock()
    mock_element = MagicMock(spec=ElementHandle)
    
    # Create selector group
    selector_group = SelectorGroup(
        "test_group",
        css("#selector1"),
        css("#selector2")
    )
    
    # Configure mock for first failure, second success
    mock_page.query_selector = AsyncMock()
    mock_page.query_selector.side_effect = [
        Error(Exception("Not found")),  # First call returns error
        Ok(mock_element)                # Second call returns success
    ]
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch the get_page method
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Execute
        result = await resolve_target(context, selector_group)
        
        # Assert
        assert result.is_ok()
        assert result.default_value(None) == mock_element
        assert mock_page.query_selector.call_count == 2


@pytest.mark.asyncio
async def test_resolve_target_with_element_handle():
    """Test resolve_target with an ElementHandle directly"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)
    mock_element = MagicMock(spec=ElementHandle)
    mock_page = MagicMock()
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Create a proper page result - important for the test to work correctly
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Fix the ElementHandle isinstance check
        with patch('silk.actions.utils.isinstance', side_effect=lambda obj, cls: 
                  True if obj is mock_element and cls is ElementHandle else isinstance(obj, cls)):
            # Execute
            result = await resolve_target(context, mock_element)
            
            # Assert
            assert result.is_ok()
            assert result.default_value(None) == mock_element


@pytest.mark.asyncio
async def test_resolve_target_with_no_page():
    """Test resolve_target when no page is available"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_page method to return error
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Error(Exception("No page")))):
        # Execute
        result = await resolve_target(context, "#test-selector")
        
        # Assert
        assert result.is_error()
        assert "No page" in str(result.error)


@pytest.mark.asyncio
async def test_resolve_target_with_no_element():
    """Test resolve_target when no element is found"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_page = MagicMock()
    
    # Configure mock to return None (no element)
    mock_page.query_selector = AsyncMock(return_value=Ok(None))
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_page method
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Execute
        result = await resolve_target(context, "#non-existent")
        
        # Assert
        assert result.is_error()
        assert "No element found" in str(result.error)


@pytest.mark.asyncio
async def test_resolve_target_with_unsupported_type():
    """Test resolve_target with an unsupported target type"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_page = MagicMock()
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_page method
    with patch.object(ActionContext, 'get_page', AsyncMock(return_value=Ok(mock_page))):
        # Execute with integer (unsupported type)
        result = await resolve_target(context, 123)
        
        # Assert
        assert result.is_error()
        assert "Unsupported target type" in str(result.error)


@pytest.mark.asyncio
async def test_validate_driver_success():
    """Test validate_driver with valid driver and page_id"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_driver = MagicMock()
    
    # Create ActionContext with page_id
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",  # Important to have a page_id
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_driver method
    with patch.object(ActionContext, 'get_driver', AsyncMock(return_value=Ok(mock_driver))):
        # Execute
        result = await validate_driver(context)
        
        # Assert
        assert result.is_ok()
        assert result.default_value(None) == mock_driver


@pytest.mark.asyncio
async def test_validate_driver_no_driver():
    """Test validate_driver when no driver is available"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    
    # Create ActionContext
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id="test-page",
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_driver method to return error
    with patch.object(ActionContext, 'get_driver', AsyncMock(return_value=Error(Exception("No driver")))):
        # Execute
        result = await validate_driver(context)
        
        # Assert
        assert result.is_error()
        assert "No driver" in str(result.error)


@pytest.mark.asyncio
async def test_validate_driver_no_page_id():
    """Test validate_driver when no page_id is set"""
    # Setup
    mock_browser_manager = MagicMock(spec=BrowserManager)  # Add spec=BrowserManager
    mock_driver = MagicMock()
    
    # Create ActionContext without page_id
    context = ActionContext(
        browser_manager=mock_browser_manager,
        context_id="test-context",
        page_id=None,  # No page_id
        retry_count=0,
        max_retries=3,
        retry_delay_ms=100,
        timeout_ms=5000,
    )
    
    # Patch get_driver method
    with patch.object(ActionContext, 'get_driver', AsyncMock(return_value=Ok(mock_driver))):
        # Execute
        result = await validate_driver(context)
        
        # Assert
        assert result.is_error()
        assert "No browser page found" in str(result.error)


@pytest.mark.asyncio
async def test_get_element_coordinates_from_tuple():
    """Test get_element_coordinates with coordinate tuple"""
    # Execute
    result = await get_element_coordinates((100, 200))
    
    # Assert
    assert result.is_ok()
    x, y = result.default_value((0, 0))
    assert x == 100.0
    assert y == 200.0


@pytest.mark.asyncio
async def test_get_element_coordinates_from_element():
    """Test get_element_coordinates with element handle"""
    # Setup
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure bounding box
    mock_element.get_bounding_box = AsyncMock(return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50}))
    
    # Execute
    result = await get_element_coordinates(mock_element)
    
    # Assert
    assert result.is_ok()
    x, y = result.default_value((0, 0))
    assert x == 10.0
    assert y == 20.0


@pytest.mark.asyncio
async def test_get_element_coordinates_from_element_with_center():
    """Test get_element_coordinates with element handle and center option"""
    # Setup
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure bounding box
    mock_element.get_bounding_box = AsyncMock(return_value=Ok({"x": 10, "y": 20, "width": 100, "height": 50}))
    
    # Create options with move_to_center=True
    options = MagicMock()
    options.move_to_center = True
    
    # Execute
    result = await get_element_coordinates(mock_element, options)
    
    # Assert
    assert result.is_ok()
    x, y = result.default_value((0, 0))
    assert x == 60.0  # 10 + 100/2
    assert y == 45.0  # 20 + 50/2


@pytest.mark.asyncio
async def test_get_element_coordinates_with_error():
    """Test get_element_coordinates when bounding box cannot be retrieved"""
    # Setup
    mock_element = MagicMock(spec=ElementHandle)
    
    # Configure bounding box to return error
    mock_element.get_bounding_box = AsyncMock(return_value=Error(Exception("No bounding box")))
    
    # Execute
    result = await get_element_coordinates(mock_element)
    
    # Assert
    assert result.is_error()
    assert "No bounding box" in str(result.error)