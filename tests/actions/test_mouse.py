import pytest
from expression import Result, Ok, Error
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch
from silk.browsers.driver import BrowserDriver
from silk.selectors.selector import Selector

from silk.actions.mouse import (
    Click,
    MouseDown,
    MouseUp,
    MouseMove,
    MouseDoubleClick, 
    MouseClick,
    Drag
)


class TestMouseActions:
    @pytest.mark.asyncio
    async def test_click_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Click action
        click_action = Click(mock_selector)
        
        result = await click_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.click.assert_called_once_with(mock_selector)

    @pytest.mark.asyncio
    async def test_click_action_with_selector_group(self, mock_driver: AsyncMock, mock_selector_group: MagicMock) -> None:
        # Test Click action with a selector group
        click_action = Click(mock_selector_group)
        
        result = await click_action.execute(mock_driver)
        
        assert result.is_ok()
        # Should try the first selector in the group
        mock_driver.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_action_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Click action failure
        mock_driver.click.side_effect = Exception("Click failed")
        click_action = Click(mock_selector)
        
        result = await click_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Click failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_mouse_down_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test MouseDown action
        button: Literal["left", "right", "middle"] = "left"
        mouse_down_action = MouseDown(mock_selector, button=button)
        
        result = await mouse_down_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.mouse_down.assert_called_once_with(mock_selector)

    @pytest.mark.asyncio
    async def test_mouse_up_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test MouseUp action
        button: Literal["left", "right", "middle"] = "left"
        mouse_up_action = MouseUp(mock_selector, button=button)
        
        result = await mouse_up_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.mouse_up.assert_called_once_with(mock_selector)

    @pytest.mark.asyncio
    async def test_mouse_move_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test MouseMove action
        offset_x, offset_y = 10, 20
        mouse_move_action = MouseMove(mock_selector, offset_x, offset_y)
        
        result = await mouse_move_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.mouse_move.assert_called_once_with(mock_selector, offset_x, offset_y)

    @pytest.mark.asyncio
    async def test_mouse_double_click_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test MouseDoubleClick action
        button: Literal["left", "right", "middle"] = "left"
        double_click_action = MouseDoubleClick(mock_selector, button=button)
        
        result = await double_click_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.double_click.assert_called_once_with(mock_selector)

    @pytest.mark.asyncio
    async def test_mouse_click_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test MouseClick action with custom options
        button: Literal["left", "right", "middle"] = "left"
        click_count = 3
        delay = 50
        force = True
        
        mouse_click_action = MouseClick(
            mock_selector, 
            button=button, 
            click_count=click_count, 
            delay=delay,
            force=force
        )
        
        result = await mouse_click_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.click_with_options.assert_called_once_with(
            mock_selector, 
            button=button, 
            click_count=click_count, 
            delay=delay,
            force=force
        )

    @pytest.mark.asyncio
    async def test_drag_action(self, mock_driver: AsyncMock, mock_selector: MagicMock, mock_selector_group: MagicMock) -> None:
        # Test Drag action
        source_offset_x, source_offset_y = 5, 10
        target_offset_x, target_offset_y = 15, 20
        button: Literal["left", "right", "middle"] = "left"
        
        drag_action = Drag(
            mock_selector,
            mock_selector_group,
            source_offset_x,
            source_offset_y,
            target_offset_x,
            target_offset_y,
            button=button
        )
        
        result = await drag_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.drag.assert_called_once_with(
            mock_selector,
            mock_selector_group.selectors[0],  # First selector in the group
            source_offset_x=source_offset_x,
            source_offset_y=source_offset_y,
            target_offset_x=target_offset_x,
            target_offset_y=target_offset_y
        )

    @pytest.mark.asyncio
    async def test_drag_action_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Drag action failure
        mock_driver.drag.side_effect = Exception("Drag failed")
        
        drag_action = Drag(mock_selector, mock_selector)
        
        result = await drag_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Drag failed" in str(result.error) 