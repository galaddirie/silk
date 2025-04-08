import pytest
from expression.core import Error, Ok

from silk.actions.input import (
    Click,
    DoubleClick,
    Drag,
    Fill,
    KeyPress,
    MouseDown,
    MouseMove,
    MouseUp,
    Select,
    Type,
)
from silk.models.browser import ClickOptions, KeyModifier, MouseMoveOptions
from silk.selectors.selector import Selector, SelectorGroup, SelectorType


class TestMouseMove:
    @pytest.mark.asyncio
    async def test_mouse_move_to_coordinates(
        self, action_context, mock_browser_context
    ):
        """Test mouse move to coordinates."""
        target = (100, 200)
        action = MouseMove(target)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_move.assert_called_once_with(
            100, 200, MouseMoveOptions()
        )

    @pytest.mark.asyncio
    async def test_mouse_move_to_element_handle(
        self, action_context, mock_element_handle, mock_browser_context
    ):
        """Test mouse move to element handle."""
        action = MouseMove(mock_element_handle)

        result = await action.execute(action_context)

        assert result.is_ok()
        # Verify it uses the center of the bounding box
        mock_browser_context.mouse_move.assert_called_once_with(
            60, 45, MouseMoveOptions()  # Center of 10,20,100,50 bounding box
        )

    @pytest.mark.asyncio
    async def test_mouse_move_to_css_selector(
        self,
        action_context,
        mock_browser_page,
        mock_element_handle,
        mock_browser_context,
    ):
        """Test mouse move to CSS selector."""
        # Setup the mock page to return our element when queried
        mock_browser_page.query_selector.return_value = Ok(mock_element_handle)

        action = MouseMove("#test-element")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.query_selector.assert_called_once_with("#test-element")
        mock_browser_context.mouse_move.assert_called_once()

    @pytest.mark.asyncio
    async def test_mouse_move_with_selector_group(
        self,
        action_context,
        mock_browser_page,
        mock_element_handle,
        mock_browser_context,
    ):
        """Test mouse move to selector group."""
        # Setup the mock page to return our element when queried
        mock_browser_page.query_selector.return_value = Ok(mock_element_handle)

        selector_group = SelectorGroup(
            "test_group",
            Selector(type=SelectorType.CSS, value="#test-element"),
        )
        action = MouseMove(selector_group)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.query_selector.assert_called_once()
        mock_browser_context.mouse_move.assert_called_once()

    @pytest.mark.asyncio
    async def test_mouse_move_with_offsets(self, action_context, mock_browser_context):
        """Test mouse move with offsets."""
        target = (100, 200)
        action = MouseMove(target, offset_x=10, offset_y=20)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_move.assert_called_once_with(
            110, 220, MouseMoveOptions()
        )

    @pytest.mark.asyncio
    async def test_mouse_move_selector_not_found(
        self, action_context, mock_browser_page
    ):
        """Test mouse move when selector is not found."""
        # Setup the mock page to return error when queried
        mock_browser_page.query_selector.return_value = Error(
            Exception("Element not found")
        )

        action = MouseMove("#nonexistent-element")

        result = await action.execute(action_context)

        assert result.is_error()
        assert "Element not found" in str(result.error)


class TestClick:
    @pytest.mark.asyncio
    async def test_click_on_coordinates(self, action_context, mock_browser_context):
        """Test click on coordinates."""
        target = (100, 200)
        action = Click(target)

        result = await action.execute(action_context)

        assert result.is_ok()
        # Verify we moved to the coordinates first
        mock_browser_context.mouse_move.assert_called_once()
        # Then clicked
        mock_browser_context.mouse_click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_on_element_handle(
        self, action_context, mock_element_handle, mock_browser_context
    ):
        """Test click on element handle."""
        action = Click(mock_element_handle)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_move.assert_called_once()
        mock_browser_context.mouse_click.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_with_custom_options(
        self, action_context, mock_browser_context
    ):
        """Test click with custom options."""
        target = (100, 200)
        options = ClickOptions(button="right", delay=100)
        action = Click(target, options)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_click.assert_called_once_with(
            "right", MouseMoveOptions(timeout=0)
        )

    @pytest.mark.asyncio
    async def test_click_position_offset(
        self, action_context, mock_browser_context, mock_element_handle
    ):
        """Test click with position offset."""
        options = ClickOptions(position_offset=(10, 15))
        action = Click(mock_element_handle, options)

        result = await action.execute(action_context)

        assert result.is_ok()
        # Should move to element + offset
        assert mock_browser_context.mouse_move.called
        mock_browser_context.mouse_click.assert_called_once()


class TestDoubleClick:
    @pytest.mark.asyncio
    async def test_double_click_on_coordinates(
        self, action_context, mock_browser_context
    ):
        """Test double click on coordinates."""
        target = (100, 200)
        action = DoubleClick(target)

        result = await action.execute(action_context)

        assert result.is_ok()
        # Verify we moved to the coordinates first
        mock_browser_context.mouse_move.assert_called_once()
        # Then clicked twice (or double clicked depending on implementation)
        assert (
            mock_browser_context.mouse_click.call_count == 2
            or mock_browser_context.mouse_double_click.call_count == 1
        )

    @pytest.mark.asyncio
    async def test_double_click_with_custom_options(
        self, action_context, mock_browser_context
    ):
        """Test double click with custom options."""
        target = (100, 200)
        options = ClickOptions(button="right", delay=100)
        action = DoubleClick(target, options)

        result = await action.execute(action_context)

        assert result.is_ok()
        # Should set click_count to 2 regardless of user options
        assert getattr(action.options, "click_count", 0) == 2


class TestFill:
    @pytest.mark.asyncio
    async def test_fill_with_selector(self, action_context, mock_browser_page):
        """Test fill with selector."""
        mock_browser_page.fill.return_value = Ok(None)

        action = Fill("#input-field", "test text")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.fill.assert_called_once_with(
            "#input-field", "test text", action.options
        )

    @pytest.mark.asyncio
    async def test_fill_with_element_handle(self, action_context, mock_element_handle):
        """Test fill with element handle."""
        action = Fill(mock_element_handle, "test text")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_element_handle.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_with_selector_group(self, action_context, mock_browser_page):
        """Test fill with selector group."""
        mock_browser_page.fill.return_value = Ok(None)

        selector_group = SelectorGroup(
            "test_group",
            Selector(type=SelectorType.CSS, value="#input-field"),
        )
        action = Fill(selector_group, "test text")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_element_not_found(self, action_context, mock_browser_page):
        """Test fill when element is not found."""
        mock_browser_page.fill.return_value = Error(Exception("Element not found"))

        action = Fill("#nonexistent-input", "test text")

        result = await action.execute(action_context)

        assert result.is_error()
        assert "Element not found" in str(result.error)


class TestType:
    @pytest.mark.asyncio
    async def test_type_is_alias_for_fill(self, action_context, mock_browser_page):
        """Test that Type is an alias for Fill."""
        mock_browser_page.fill.return_value = Ok(None)

        action = Type("#input-field", "test text")

        result = await action.execute(action_context)

        assert result.is_ok()
        # Verify Type internally uses Fill
        assert hasattr(action, "fill_action")
        mock_browser_page.fill.assert_called_once()


class TestKeyPress:
    @pytest.mark.asyncio
    async def test_key_press_single_key(self, action_context, mock_browser_context):
        """Test key press for a single key."""
        action = KeyPress("Enter")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.key_press.assert_called_once()

    @pytest.mark.asyncio
    async def test_key_press_with_modifiers(self, action_context, mock_browser_context):
        """Test key press with modifiers."""
        action = KeyPress("a", modifiers=[KeyModifier.CTRL, KeyModifier.SHIFT])

        result = await action.execute(action_context)

        assert result.is_ok()
        # Should press down modifiers first
        assert mock_browser_context.key_down.call_count == 2
        # Then press the key
        mock_browser_context.key_press.assert_called_once()
        # Then release modifiers
        assert mock_browser_context.key_up.call_count == 2


class TestDrag:
    @pytest.mark.asyncio
    async def test_drag_coordinates_to_coordinates(
        self, action_context, mock_browser_context
    ):
        """Test drag from coordinates to coordinates."""
        source = (10, 20)
        target = (100, 200)
        action = Drag(source, target)

        mock_browser_context.mouse_drag.return_value = Ok(None)

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_drag.assert_called_once_with(
            source, target, action.options
        )

    @pytest.mark.asyncio
    async def test_drag_element_to_element(
        self,
        action_context,
        mock_browser_page,
        mock_element_handle,
        mock_browser_context,
    ):
        """Test drag from element to element."""
        # Setup mock page to return elements
        mock_browser_page.query_selector.return_value = Ok(mock_element_handle)
        mock_browser_context.mouse_drag.return_value = Ok(None)

        source_selector = "#source-element"
        target_selector = "#target-element"
        action = Drag(source_selector, target_selector)

        result = await action.execute(action_context)

        assert result.is_ok()
        assert mock_browser_page.query_selector.call_count == 2
        mock_browser_context.mouse_drag.assert_called_once()

    @pytest.mark.asyncio
    async def test_drag_element_not_found(self, action_context, mock_browser_page):
        """Test drag when element is not found."""
        mock_browser_page.query_selector.return_value = Error(
            Exception("Element not found")
        )

        action = Drag("#nonexistent-source", "#target-element")

        result = await action.execute(action_context)

        assert result.is_error()
        assert "Element not found" in str(result.error)


class TestSelect:
    @pytest.mark.asyncio
    async def test_select_by_value(self, action_context, mock_browser_page):
        """Test select option by value."""
        mock_browser_page.select.return_value = Ok(None)

        action = Select("#dropdown", value="option1")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.select.assert_called_once_with("#dropdown", "option1", None)

    @pytest.mark.asyncio
    async def test_select_by_text(self, action_context, mock_browser_page):
        """Test select option by text."""
        mock_browser_page.select.return_value = Ok(None)

        action = Select("#dropdown", text="Option 1")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.select.assert_called_once_with("#dropdown", None, "Option 1")

    @pytest.mark.asyncio
    async def test_select_with_element_handle(
        self, action_context, mock_element_handle, mock_browser_page
    ):
        """Test select with element handle."""
        mock_browser_page.execute_script.return_value = Ok({"success": True})

        action = Select(mock_element_handle, value="option1")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.execute_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_select_option_not_found(self, action_context, mock_browser_page):
        """Test select when option is not found."""
        mock_browser_page.select.return_value = Error(Exception("Option not found"))

        action = Select("#dropdown", value="nonexistent-option")

        result = await action.execute(action_context)

        assert result.is_error()
        assert "Option not found" in str(result.error)

    @pytest.mark.asyncio
    async def test_select_no_value_or_text(self):
        """Test select with neither value nor text provided."""
        with pytest.raises(ValueError):
            Select("#dropdown")


class TestMouseUpDown:
    @pytest.mark.asyncio
    async def test_mouse_down(self, action_context, mock_browser_context):
        """Test mouse down action."""
        action = MouseDown("left")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_down.assert_called_once_with(
            "left", MouseMoveOptions()
        )

    @pytest.mark.asyncio
    async def test_mouse_up(self, action_context, mock_browser_context):
        """Test mouse up action."""
        action = MouseUp("right")

        result = await action.execute(action_context)

        assert result.is_ok()
        mock_browser_context.mouse_up.assert_called_once_with(
            "right", MouseMoveOptions()
        )
