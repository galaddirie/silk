"""
Input actions for interacting with elements via mouse or keyboard in the browser.
"""

import logging
from typing import Any, List, Optional, Union

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.browsers.element import ElementHandle
from silk.models.browser import (
    ActionContext,
    ClickOptions,
    CoordinateType,
    DragOptions,
    KeyModifier,
    KeyPressOptions,
    MouseButtonLiteral,
    MouseMoveOptions,
    TypeOptions,
)
from silk.selectors.selector import Selector, SelectorGroup, SelectorType

logger = logging.getLogger(__name__)


class MouseMove(Action[None]):
    """
    Action to move the mouse to an element or specific coordinates

    Args:
        target: Target selector, element, or coordinates
        offset_x: X offset from target
        offset_y: Y offset from target
        options: Additional movement options
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        offset_x: int = 0,
        offset_y: int = 0,
        options: Optional[MouseMoveOptions] = None,
    ):
        self.target = target
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.options = options or MouseMoveOptions()

        if isinstance(target, tuple):
            self.target_desc = f"coordinates ({target[0]}, {target[1]})"
        elif isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Move mouse to the target element or coordinates"""
        try:
            logger.debug(
                f"Moving mouse to {self.target_desc} with offset ({self.offset_x}, {self.offset_y})"
            )

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            if isinstance(self.target, tuple):
                x, y = self.target
                return await browser_context.mouse_move(
                    x + self.offset_x, y + self.offset_y, self.options
                )
            elif isinstance(self.target, ElementHandle):
                bbox_result = await self.target.get_bounding_box()
                if bbox_result.is_error():
                    return Error(bbox_result.error)

                bbox = bbox_result.default_value(None)
                if bbox is None:
                    return Error(Exception("Failed to get bounding box"))
                center_x = int(bbox["x"] + bbox["width"] / 2)
                center_y = int(bbox["y"] + bbox["height"] / 2)

                return await browser_context.mouse_move(
                    center_x + self.offset_x, center_y + self.offset_y, self.options
                )
            elif isinstance(self.target, SelectorGroup):
                selector_result = await self.target.execute(
                    lambda selector: self._move_to_selector(selector, context)
                )
                if selector_result.is_error():
                    return Error(selector_result.error)
                return Ok(None)
            else:
                selector = (
                    self.target
                    if isinstance(self.target, Selector)
                    else Selector(type=SelectorType.CSS, value=self.target)
                )
                result = await self._move_to_selector(selector, context)
                if result.is_error():
                    return Error(result.error)
                return Ok(None)

        except Exception as e:
            logger.error(f"Error moving mouse to {self.target_desc}: {e}")
            return Error(e)

    async def _move_to_selector(
        self, selector: Selector, context: ActionContext
    ) -> Result[None, Exception]:
        """Helper method to move to an element found by selector"""
        try:
            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            element_result = await page.query_selector(selector.value)
            if element_result.is_error():
                return Error(
                    Exception(
                        f"Failed to find element with {selector}: {element_result.error}"
                    )
                )

            element = element_result.default_value(None)
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))

            bbox_result = await element.get_bounding_box()
            if bbox_result.is_error():
                return Error(bbox_result.error)

            bbox = bbox_result.default_value(None)
            if bbox is None:
                return Error(Exception("Failed to get bounding box"))
            center_x = int(bbox["x"] + bbox["width"] / 2)
            center_y = int(bbox["y"] + bbox["height"] / 2)

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            return await browser_context.mouse_move(
                center_x + self.offset_x, center_y + self.offset_y, self.options
            )
        except Exception as e:
            return Error(e)


class Click(Action[None]):
    """
    Action to click an element

    Args:
        target: Target selector, element, or coordinates
        options: Additional click options
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        options: Optional[ClickOptions] = None,
    ):
        self.target = target
        self.options = options or ClickOptions()

        if isinstance(target, tuple):
            self.target_desc = f"coordinates ({target[0]}, {target[1]})"
        elif isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Click on the target element or coordinates"""
        try:
            logger.debug(f"Clicking on {self.target_desc}")

            move_action = MouseMove(
                self.target,
                offset_x=(
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[0]
                ),
                offset_y=(
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[1]
                ),
            )
            move_result = await move_action.execute(context)

            if move_result.is_error():
                return Error(move_result.error)

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            # Create mouse options with same timeout from click options
            mouse_options = MouseMoveOptions(timeout=0)
            return await browser_context.mouse_click(self.options.button, mouse_options)

        except Exception as e:
            logger.error(f"Error clicking on {self.target_desc}: {e}")
            return Error(e)


class DoubleClick(Action[None]):
    """
    Action to double-click an element

    Args:
        target: Target selector, element, or coordinates
        options: Additional click options
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        options: Optional[ClickOptions] = None,
    ):
        if options is None:
            self.options = ClickOptions(click_count=2)
        else:
            options_dict = options.model_dump()
            options_dict["click_count"] = 2
            self.options = ClickOptions(**options_dict)

        self.target = target

        if isinstance(target, tuple):
            self.target_desc = f"coordinates ({target[0]}, {target[1]})"
        elif isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Double-click on the target element or coordinates"""
        try:
            logger.debug(f"Double-clicking on {self.target_desc}")

            move_action = MouseMove(
                self.target,
                offset_x=(
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[0]
                ),
                offset_y=(
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[1]
                ),
            )
            move_result = await move_action.execute(context)

            if move_result.is_error():
                return Error(move_result.error)

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            mouse_options = MouseMoveOptions(timeout=self.options.timeout)

            if isinstance(self.target, tuple):
                x, y = self.target
                offset_x = (
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[0]
                )
                offset_y = (
                    0
                    if self.options.position_offset is None
                    else self.options.position_offset[1]
                )

                return await browser_context.mouse_double_click(
                    x + offset_x, y + offset_y, mouse_options
                )
            else:
                click_result = await browser_context.mouse_click(
                    self.options.button, mouse_options
                )
                if click_result.is_error():
                    return Error(click_result.error)

                return await browser_context.mouse_click(
                    self.options.button, mouse_options
                )

        except Exception as e:
            logger.error(f"Error double-clicking on {self.target_desc}: {e}")
            return Error(e)


class MouseDown(Action[None]):
    """
    Action to press a mouse button

    Args:
        button: Mouse button to press
        options: Additional mouse options
    """

    def __init__(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseMoveOptions] = None,
    ):
        self.button = button
        self.options = options or MouseMoveOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Press the specified mouse button"""
        try:
            logger.debug(f"Pressing {self.button} mouse button")

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            return await browser_context.mouse_down(self.button, self.options)
        except Exception as e:
            logger.error(f"Error pressing {self.button} mouse button: {e}")
            return Error(e)


class MouseUp(Action[None]):
    """
    Action to release a mouse button

    Args:
        button: Mouse button to release
        options: Additional mouse options
    """

    def __init__(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseMoveOptions] = None,
    ):
        self.button = button
        self.options = options or MouseMoveOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Release the specified mouse button"""
        try:
            logger.debug(f"Releasing {self.button} mouse button")

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            return await browser_context.mouse_up(self.button, self.options)
        except Exception as e:
            logger.error(f"Error releasing {self.button} mouse button: {e}")
            return Error(e)


class Drag(Action[None]):
    """
    Action to drag from one element/position to another

    Args:
        source: Source element or position
        target: Target element or position
        options: Additional drag options
    """

    def __init__(
        self,
        source: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        target: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        options: Optional[DragOptions] = None,
    ):
        self.source = source
        self.target = target
        self.options = options or DragOptions()

        def get_desc(
            item: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        ) -> str:
            if isinstance(item, tuple):
                return f"coordinates ({item[0]}, {item[1]})"
            elif isinstance(item, str):
                return f"selector '{item}'"
            elif isinstance(item, Selector):
                return f"{item}"
            elif isinstance(item, SelectorGroup):
                return f"selector group '{item.name}'"
            else:
                return "element handle"

        self.source_desc = get_desc(source)
        self.target_desc = get_desc(target)

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Drag from source to target"""
        try:
            logger.debug(f"Dragging from {self.source_desc} to {self.target_desc}")

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            source_resolved = await self._resolve_item(self.source, context)
            if source_resolved.is_error():
                return Error(source_resolved.error)

            target_resolved = await self._resolve_item(self.target, context)
            if target_resolved.is_error():
                return Error(target_resolved.error)

            source = source_resolved.default_value(None)
            target = target_resolved.default_value(None)
            if source is None:
                return Error(Exception("Failed to get source"))
            if target is None:
                return Error(Exception("Failed to get target"))

            drag_result = await browser_context.mouse_drag(source, target, self.options)

            if drag_result.is_error():
                return Error(drag_result.error)
            return Ok(None)
        except Exception as e:
            logger.error(
                f"Error dragging from {self.source_desc} to {self.target_desc}: {e}"
            )
            return Error(e)

    async def _resolve_item(
        self,
        item: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        context: ActionContext,
    ) -> Result[Union[ElementHandle, CoordinateType], Exception]:
        """Resolve a selector/group to an element or coordinates"""
        try:
            if isinstance(item, (tuple, ElementHandle)):
                return Ok(item)
            elif isinstance(item, SelectorGroup):
                if not item.selectors:
                    return Error(Exception("Selector group is empty"))
                first_selector = item.selectors[0]
                return await self._resolve_item(first_selector, context)
            else:
                selector = (
                    item
                    if isinstance(item, Selector)
                    else Selector(type=SelectorType.CSS, value=item)
                )

                page_result = await context.get_page()
                if page_result.is_error():
                    return Error(page_result.error)

                page = page_result.default_value(None)
                if page is None:
                    return Error(Exception("Failed to get page"))

                element_result = await page.query_selector(selector.value)
                if element_result.is_error():
                    return Error(element_result.error)

                element = element_result.default_value(None)
                if element is None:
                    return Error(Exception(f"Element not found: {selector}"))

                return Ok(element)
        except Exception as e:
            return Error(e)


class Fill(Action[None]):
    """
    Action to fill an input field with text

    Args:
        target: Target input element
        text: Text to input
        options: Additional typing options
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        text: str,
        options: Optional[TypeOptions] = None,
    ):
        self.target = target
        self.text = text
        self.options = options or TypeOptions()

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Fill text into the target element"""
        try:
            logger.debug(f"Filling '{self.text}' into {self.target_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            if isinstance(self.target, ElementHandle):
                return await self.target.fill(self.text, self.options)
            elif isinstance(self.target, SelectorGroup):
                selector_result = await self.target.execute(
                    lambda selector: self._fill_selector(selector, page)
                )
                if selector_result.is_error():
                    return Error(selector_result.error)
                return Ok(None)
            else:
                selector = (
                    self.target
                    if isinstance(self.target, Selector)
                    else Selector(type=SelectorType.CSS, value=self.target)
                )
                fill_result = await self._fill_selector(selector, page)
                if fill_result.is_error():
                    return Error(fill_result.error)
                return Ok(None)

        except Exception as e:
            logger.error(f"Error filling text into {self.target_desc}: {e}")
            return Error(e)

    async def _fill_selector(
        self, selector: Selector, page: Any
    ) -> Result[None, Exception]:
        """Helper method to fill an element found by selector"""
        try:
            fill_result = await page.fill(selector.value, self.text, self.options)
            if fill_result.is_error():
                return Error(fill_result.error)
            return Ok(None)
        except Exception as e:
            return Error(e)


class Type(Action[None]):
    """
    Action to type text (alias for Fill with more intuitive name)

    Args:
        target: Target input element
        text: Text to type
        options: Additional typing options
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        text: str,
        options: Optional[TypeOptions] = None,
    ):
        self.fill_action = Fill(target, text, options)

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Type text into the target element using Fill action"""
        return await self.fill_action.execute(context)


class KeyPress(Action[None]):
    """
    Action to press a key or key combination

    Args:
        key: Key or key combination to press
        modifiers: List of keyboard modifiers to apply
    """

    def __init__(self, key: str, modifiers: Optional[List[KeyModifier]] = None):
        self.key = key
        self.modifiers = modifiers or []
        self.options = TypeOptions()

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Press key with optional modifiers"""
        try:
            logger.debug(
                f"Pressing key '{self.key}' with modifiers {[m.name for m in self.modifiers]}"
            )

            if context.browser_manager is None:
                return Error(Exception("Browser manager is not available"))

            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            for modifier in self.modifiers:
                key_down_result = await browser_context.key_down(modifier.name.lower())
                if key_down_result.is_error():
                    return Error(key_down_result.error)

            key_options = KeyPressOptions(key=self.key)
            key_press_result = await browser_context.key_press(self.key, key_options)

            for modifier in reversed(self.modifiers):
                await browser_context.key_up(modifier.name.lower())

            if key_press_result.is_error():
                return Error(key_press_result.error)

            return Ok(None)
        except Exception as e:
            logger.error(f"Error pressing key '{self.key}': {e}")
            return Error(e)


class Select(Action[None]):
    """
    Action to select an option from a dropdown

    Args:
        target: Target select element
        value: Option value to select
        text: Option text to select (alternative to value)
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        value: Optional[str] = None,
        text: Optional[str] = None,
    ):
        self.target = target
        self.value = value
        self.text = text

        if not value and not text:
            raise ValueError("Either value or text must be provided")

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Select an option from the dropdown"""
        try:
            select_by = f"value='{self.value}'" if self.value else f"text='{self.text}'"
            logger.debug(f"Selecting option with {select_by} from {self.target_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            if isinstance(self.target, ElementHandle):
                bbox_result = await self.target.get_bounding_box()
                if bbox_result.is_error():
                    return Error(
                        Exception(f"Cannot get element position: {bbox_result.error}")
                    )

                script = """
                    const elemFromPoint = document.elementFromPoint(arguments[0], arguments[1]);
                    if (!elemFromPoint) return { success: false, error: 'Element not found at position' };

                    const select = elemFromPoint.closest('select') || elemFromPoint;
                    if (select.tagName !== 'SELECT') return { success: false, error: 'Element is not a select' };

                    if (arguments[2]) {
                        const option = Array.from(select.options).find(opt => opt.value === arguments[2]);
                        if (option) {
                            option.selected = true;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            return { success: true };
                        } else {
                            return { success: false, error: 'Option with specified value not found' };
                        }
                    } else if (arguments[3]) {
                        const option = Array.from(select.options).find(opt => opt.text === arguments[3]);
                        if (option) {
                            option.selected = true;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            return { success: true };
                        } else {
                            return { success: false, error: 'Option with specified text not found' };
                        }
                    }

                    return { success: false, error: 'No value or text provided' };
                """

                bbox = bbox_result.default_value(None)
                if bbox is None:
                    return Error(Exception("Failed to get bounding box"))
                center_x = bbox["x"] + bbox["width"] / 2
                center_y = bbox["y"] + bbox["height"] / 2

                result = await page.execute_script(
                    script, center_x, center_y, self.value, self.text
                )

                if result.is_error():
                    return Error(result.error)

                script_result = result.default_value(None)
                if isinstance(script_result, dict) and not script_result.get(
                    "success", False
                ):
                    return Error(
                        Exception(script_result.get("error", "Failed to select option"))
                    )

                return Ok(None)
            elif isinstance(self.target, SelectorGroup):
                for selector in self.target.selectors:
                    result = await page.select(selector.value, self.value, self.text)

                    if result.is_ok():
                        return Ok(None)

                return Error(Exception("Failed to select from any selector in group"))
            else:
                selector_value = (
                    self.target.value
                    if isinstance(self.target, Selector)
                    else self.target
                )

                result = await page.select(selector_value, self.value, self.text)
                if result.is_error():
                    return Error(result.error)

                return Ok(None)
        except Exception as e:
            logger.error(f"Error selecting option from {self.target_desc}: {e}")
            return Error(e)
