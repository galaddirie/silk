from typing import Optional, Union, Tuple, Literal
from expression.core import Result, Ok, Error
from expression import pipe

from silk.browser.driver import BrowserDriver, ElementHandle
from silk.selectors.selector import Selector, SelectorGroup
from silk.actions.base import Action
from silk.actions.utils import _find_element_and_perform

from enum import Enum, auto


class MouseButton(Enum):
    """Enum representing mouse buttons for mouse actions"""
    LEFT = auto()
    MIDDLE = auto()
    RIGHT = auto()

MouseButtonStr = Literal["left", "middle", "right"]


class MouseMove(Action[None]):
    """Action to move the mouse to an element or specific coordinates
    Args:
        target: The target to move to
        offset_x: The x offset to move to
        offset_y: The y offset to move to
    """

    coordinates: Optional[Tuple[int, int]] = None
    selector: Optional[Union[Selector, SelectorGroup]] = None

    def __init__(
        self,
        target: Union[Selector, SelectorGroup, Tuple[int, int]],
        offset_x: int = 0,
        offset_y: int = 0,
    ):
        if isinstance(target, tuple):
            target_str = f"({target[0]}, {target[1]})"
            self.coordinates = target
            self.selector = None
        else:
            target_str = (
                target.name if isinstance(target, SelectorGroup) else str(target)
            )
            self.coordinates = None
            self.selector = target

        super().__init__(
            name=f"mouse_move({target_str}, offset_x={offset_x}, offset_y={offset_y})",
            description=f"Move mouse to {target_str} with offset ({offset_x}, {offset_y})",
        )
        self.offset_x = offset_x
        self.offset_y = offset_y

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            if self.coordinates:
                # Move to absolute coordinates
                await driver.mouse_move(self.coordinates[0], self.coordinates[1])
                return Ok(None)
            if self.selector is None:
                return Error(Exception("Selector is None"))
            # Move to element
            if isinstance(self.selector, SelectorGroup):
                result = await self.selector.execute(
                    lambda sel: self._move_to_element(driver, sel)
                )
                if result.is_error():
                    return result
                return Ok(None)
            else:
                
                return await self._move_to_element(driver, self.selector)
        except Exception as e:
            return Error(e)

    async def _move_to_element(
        self, driver: BrowserDriver, selector: Selector
    ) -> Result[None, Exception]:
        try:
            element = await driver.query_selector(selector.value)
            if element:
                await driver.mouse_move_to_element(
                    element, self.offset_x, self.offset_y
                )
                return Ok(None)
            else:
                return Error(Exception(f"Element not found: {selector}"))
        except Exception as e:
            return Error(e)


class MouseDown(Action[None]):
    """Action to press a mouse button
    Args:
        button: The button to press
    """

    def __init__(self, button: MouseButtonStr = "left"):
        super().__init__(
            name=f"mouse_down(button={button})",
            description=f"Press the {button} mouse button",
        )
        self.button = button

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.mouse_down(self.button)
            return Ok(None)
        except Exception as e:
            return Error(e)


class MouseUp(Action[None]):
    """Action to release a mouse button
    Args:
        button: The button to release
    """

    def __init__(self, button: MouseButtonStr = "left"):
        super().__init__(
            name=f"mouse_up(button={button})",
            description=f"Release the {button} mouse button",
        )
        self.button = button

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.mouse_up(self.button)
            return Ok(None)
        except Exception as e:
            return Error(e)


class Click(Action[None]):
    """Action to click an element
    Args:
        selector: The selector to click on
    """

    def __init__(self, selector: Union[Selector, SelectorGroup]):
        selector_str = (
            selector.name if isinstance(selector, SelectorGroup) else str(selector)
        )
        super().__init__(
            name=f"click({selector_str})",
            description=f"Click on element: {selector_str}",
        )
        self.selector = selector

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            if isinstance(self.selector, SelectorGroup):
                result = await self.selector.execute(
                    lambda sel: _find_element_and_perform(
                        driver, sel, lambda el: el.click()
                    )
                )
                if result.is_error():
                    return result
                return Ok(None)
            else:
                return await _find_element_and_perform(
                    driver, self.selector, lambda el: el.click()
                )
        except Exception as e:
            return Error(e)


class MouseClick(Action[None]):
    """Action to click a mouse button (down and up)"""

    def __init__(
        self,
        button: MouseButtonStr = "left",
        click_count: int = 1,
        delay_between_ms: Optional[int] = None,
    ):
        super().__init__(
            name=f"mouse_click(button={button}, count={click_count})",
            description=f"Click the {button} mouse button {click_count} time(s)",
        )
        self.button = button
        self.click_count = click_count
        self.delay_between_ms = delay_between_ms

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.mouse_click(
                button=self.button,
                click_count=self.click_count,
                delay_between_ms=self.delay_between_ms,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)


class MouseDoubleClick(Action[None]):
    """Action to double click a mouse button
    Args:
        button: The button to double click
    """

    def __init__(self, button: MouseButtonStr = "left"):
        super().__init__(
            name=f"mouse_double_click(button={button})",
            description=f"Double click the {button} mouse button",
        )
        self.button = button

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.mouse_double_click(self.button)
            return Ok(None)
        except Exception as e:
            return Error(e)


class Drag(Action[None]):
    """Action to drag from one element/position to another
    Args:
        source: The source to drag from
        target: The target to drag to
        source_offset_x: The x offset to drag from
        source_offset_y: The y offset to drag from
        target_offset_x: The x offset to drag to
        target_offset_y: The y offset to drag to
    """

    def __init__(
        self,
        source: Union[Selector, SelectorGroup, Tuple[int, int]],
        target: Union[Selector, SelectorGroup, Tuple[int, int]],
        source_offset_x: int = 0,
        source_offset_y: int = 0,
        target_offset_x: int = 0,
        target_offset_y: int = 0,
    ):
        # Format source string
        if isinstance(source, tuple):
            source_str = f"({source[0]}, {source[1]})"
        else:
            source_str = (
                source.name if isinstance(source, SelectorGroup) else str(source)
            )

        # Format target string
        if isinstance(target, tuple):
            target_str = f"({target[0]}, {target[1]})"
        else:
            target_str = (
                target.name if isinstance(target, SelectorGroup) else str(target)
            )

        super().__init__(
            name=f"drag({source_str} → {target_str})",
            description=f"Drag from {source_str} to {target_str}",
        )
        self.source = source
        self.target = target
        self.source_offset_x = source_offset_x
        self.source_offset_y = source_offset_y
        self.target_offset_x = target_offset_x
        self.target_offset_y = target_offset_y

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            # Move to source
            move_to_source = MouseMove(
                self.source,
                offset_x=self.source_offset_x,
                offset_y=self.source_offset_y,
            )
            source_result = await move_to_source.execute(driver)
            if source_result.is_error():
                return source_result

            # Press mouse button
            mouse_down = MouseDown()
            down_result = await mouse_down.execute(driver)
            if down_result.is_error():
                return down_result

            # Move to target
            move_to_target = MouseMove(
                self.target,
                offset_x=self.target_offset_x,
                offset_y=self.target_offset_y,
            )
            target_result = await move_to_target.execute(driver)
            if target_result.is_error():
                return target_result

            # Release mouse button
            mouse_up = MouseUp()
            return await mouse_up.execute(driver)
        except Exception as e:
            return Error(e)
