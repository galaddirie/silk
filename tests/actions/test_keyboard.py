import pytest
from expression import Result, Ok, Error
from unittest.mock import AsyncMock, MagicMock, patch
from silk.browsers.driver import BrowserDriver
from silk.selectors.selector import Selector, SelectorGroup


from silk.actions.keyboard import (
    Type, 
    KeyDown,
    KeyUp,
    KeyPress,
    Shortcut
)


class TestKeyboardActions:
    @pytest.mark.asyncio
    async def test_type_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Type action
        text = "Hello, World!"
        type_action = Type(mock_selector, text)
        
        result = await type_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.fill.assert_called_once_with(mock_selector, text)

    @pytest.mark.asyncio
    async def test_type_action_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Type action failure
        mock_driver.fill.side_effect = Exception("Type failed")
        text = "Hello, World!"
        type_action = Type(mock_selector, text)
        
        result = await type_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Type failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_type_action_with_selector_group(self, mock_driver: AsyncMock, mock_selector_group: MagicMock) -> None:
        # Test Type action with a selector group
        text = "Hello, Group!"
        type_action = Type(mock_selector_group, text)
        
        result = await type_action.execute(mock_driver)
        
        assert result.is_ok()
        # Should try with the first selector in the group
        mock_driver.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_key_down_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test KeyDown action
        key = "Shift"
        key_down_action = KeyDown(key)
        
        result = await key_down_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.key_down.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_key_up_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test KeyUp action
        key = "Control"
        key_up_action = KeyUp(key)
        
        result = await key_up_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.key_up.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_key_press_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test KeyPress action
        key = "Enter"
        key_press_action = KeyPress(key)
        
        result = await key_press_action.execute(mock_driver)
        
        assert result.is_ok()
        mock_driver.press.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_key_press_action_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test KeyPress action failure
        mock_driver.press.side_effect = Exception("Press failed")
        key = "Tab"
        key_press_action = KeyPress(key)
        
        result = await key_press_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Press failed" in str(result.error)


    @pytest.mark.asyncio
    async def test_shortcut_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Shortcut action
        keys = ["Control", "c"]
        shortcut_action = Shortcut(*keys)
        
        result = await shortcut_action.execute(mock_driver)
        
        assert result.is_ok()
        
        # Verify that key_down was called for each key in order
        assert mock_driver.key_down.call_count == len(keys)
        mock_driver.key_down.assert_any_call(keys[0])
        mock_driver.key_down.assert_any_call(keys[1])
        
        # Verify that key_up was called for each key in reverse order
        assert mock_driver.key_up.call_count == len(keys)
        mock_driver.key_up.assert_any_call(keys[1])
        mock_driver.key_up.assert_any_call(keys[0])

    @pytest.mark.asyncio
    async def test_shortcut_action_multiple_keys(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test Shortcut action with multiple keys (e.g., Ctrl+Shift+A)
        keys = ["Control", "Shift", "a"]
        shortcut_action = Shortcut(*keys)
        
        result = await shortcut_action.execute(mock_driver)
        
        assert result.is_ok()
        assert mock_driver.key_down.call_count == len(keys)
        assert mock_driver.key_up.call_count == len(keys)
        
        # Check correct order of key presses and releases
        for i, key in enumerate(keys):
            mock_driver.key_down.assert_any_call(key)
            
        for i, key in enumerate(reversed(keys)):
            mock_driver.key_up.assert_any_call(key) 