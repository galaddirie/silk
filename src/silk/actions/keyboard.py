from typing import Optional, List, Union
from expression.core import Result, Ok, Error
from expression import pipe
from silk.browser.driver import BrowserDriver
from silk.actions.base import Action
from silk.actions.utils import _find_element_and_perform
from silk.selectors import Selector, SelectorGroup


class KeyPress(Action[None]):
    """Press a single key or a key combination"""

    def __init__(self, key: str, description: Optional[str] = None):
        """
        Initialize a key press action

        Args:
            key: Key or key combination to press (e.g., 'a', 'Enter', 'Control+c')
            description: Optional description of the action
        """
        super().__init__(
            name=f"press({key})", description=description or f"Press key: {key}"
        )
        self.key = key

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.press(self.key)
            return Ok(None)
        except Exception as e:
            return Error(e)


class KeyDown(Action[None]):
    """Press and hold a key"""

    def __init__(self, key: str, description: Optional[str] = None):
        """
        Initialize a key down action

        Args:
            key: Key to press and hold
            description: Optional description of the action
        """
        super().__init__(
            name=f"keyDown({key})",
            description=description or f"Press and hold key: {key}",
        )
        self.key = key

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.key_down(self.key)
            return Ok(None)
        except Exception as e:
            return Error(e)


class KeyUp(Action[None]):
    """Release a key"""

    def __init__(self, key: str, description: Optional[str] = None):
        """
        Initialize a key up action

        Args:
            key: Key to release
            description: Optional description of the action
        """
        super().__init__(
            name=f"keyUp({key})", description=description or f"Release key: {key}"
        )
        self.key = key

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.key_up(self.key)
            return Ok(None)
        except Exception as e:
            return Error(e)


class Type(Action[None]):
    """Action to type text into an input element"""

    def __init__(self, selector: Union[Selector, SelectorGroup], text: str):
        selector_str = (
            selector.name if isinstance(selector, SelectorGroup) else str(selector)
        )
        super().__init__(
            name=f"type({selector_str}, {text})",
            description=f"Type '{text}' into element: {selector_str}",
        )
        self.selector = selector
        self.text = text

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            if isinstance(self.selector, SelectorGroup):
                result = await self.selector.execute(
                    lambda sel: _find_element_and_perform(
                        driver, sel, lambda el: el.type(self.text)
                    )
                )
                if result.is_error():
                    return result
                return Ok(None)
            else:
                return await _find_element_and_perform(
                    driver, self.selector, lambda el: el.type(self.text)
                )
        except Exception as e:
            return Error(e)


class TypeText(Action[None]):
    """Type a sequence of characters"""

    def __init__(
        self,
        text: str,
        delay: Optional[float] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize a type text action

        Args:
            text: Text to type
            delay: Optional delay between keystrokes in milliseconds
            description: Optional description of the action
        """
        super().__init__(
            name=f"type({text[:10]}{'...' if len(text) > 10 else ''})",
            description=description or f"Type text: {text}",
        )
        self.text = text
        self.delay = delay

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            await driver.type(self.text, delay=self.delay)
            return Ok(None)
        except Exception as e:
            return Error(e)


class Shortcut(Action[None]):
    """Execute a keyboard shortcut"""

    def __init__(self, *keys: str, description: Optional[str] = None):
        """
        Initialize a keyboard shortcut action

        Args:
            *keys: Keys to press in combination
            description: Optional description of the action
        """
        key_combo = "+".join(keys)
        super().__init__(
            name=f"shortcut({key_combo})",
            description=description or f"Execute keyboard shortcut: {key_combo}",
        )
        self.keys = keys

    async def execute(self, driver: BrowserDriver) -> Result[None, Exception]:
        try:
            # Press all keys in sequence
            for key in self.keys[:-1]:
                await driver.key_down(key)

            # Press and release the last key
            await driver.press(self.keys[-1])

            # Release all keys in reverse order
            for key in reversed(self.keys[:-1]):
                await driver.key_up(key)

            return Ok(None)
        except Exception as e:
            return Error(e)
