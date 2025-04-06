"""
Input actions for interacting with elements via mouse or keyboard in the browser.
"""

from typing import Optional, Union, Tuple, List, Dict, Any, cast
from expression.core import Result, Ok, Error
import logging

from silk.browsers.driver import BrowserDriver
from silk.models.browser import (
    ElementHandle, CoordinateType, MouseButtonLiteral,
    ClickOptions, TypeOptions, MouseMoveOptions, DragOptions,
    MouseButton, KeyModifier, ActionContext
)
from silk.actions.base import Action
from silk.selectors.selector import Selector, SelectorGroup

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
        options: Optional[MouseMoveOptions] = None
    ):
        self.target = target
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.options = options or MouseMoveOptions()
        
        # Generate description for logging
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
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Move mouse to the target element or coordinates"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Moving mouse to {self.target_desc} with offset ({self.offset_x}, {self.offset_y})")
            
            if isinstance(self.target, tuple):
                # Move to specific coordinates
                x, y = self.target
                return await driver.mouse_move(
                    x + self.offset_x, 
                    y + self.offset_y, 
                    self.options
                )
            elif isinstance(self.target, ElementHandle):
                # Move to element handle
                return await driver.mouse_move_to_element(
                    self.target, 
                    self.offset_x, 
                    self.offset_y, 
                    self.options
                )
            elif isinstance(self.target, SelectorGroup):
                # Try each selector in the group
                return await self.target.execute(
                    lambda selector: self._move_to_selector(driver, selector, ctx)
                )
            else:
                # Convert string to Selector if needed
                selector = self.target if isinstance(self.target, Selector) else Selector(
                    type="css", value=self.target
                )
                return await self._move_to_selector(driver, selector, ctx)
                
        except Exception as e:
            logger.error(f"Error moving mouse to {self.target_desc}: {e}")
            return Error(e)
    
    async def _move_to_selector(
        self, driver: BrowserDriver, selector: Selector, context: ActionContext
    ) -> Result[None, Exception]:
        """Helper method to move to an element found by selector"""
        try:
            # Find the element
            element_result = await driver.query_selector(selector.value)
            if element_result.is_error():
                return Error(Exception(f"Failed to find element with {selector}: {element_result.error}"))
            
            element = element_result.value
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))
            
            # Move to the element
            return await driver.mouse_move_to_element(
                element, 
                self.offset_x, 
                self.offset_y, 
                self.options
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
        options: Optional[ClickOptions] = None
    ):
        self.target = target
        self.options = options or ClickOptions()
        
        # Generate description for logging
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
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Click on the target element or coordinates"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Clicking on {self.target_desc}")
            
            # First move to the target
            move_action = MouseMove(self.target, 
                                   offset_x=0 if self.options.position_offset is None else self.options.position_offset[0],
                                   offset_y=0 if self.options.position_offset is None else self.options.position_offset[1])
            move_result = await move_action.execute(driver, ctx)
            
            if move_result.is_error():
                return move_result
            
            # Then perform the click
            if isinstance(self.target, tuple):
                # Click at specific coordinates
                x, y = self.target
                offset_x = 0 if self.options.position_offset is None else self.options.position_offset[0]
                offset_y = 0 if self.options.position_offset is None else self.options.position_offset[1]
                
                return await driver.click(
                    x + offset_x,
                    y + offset_y,
                    self.options
                )
            elif isinstance(self.target, ElementHandle):
                # Click element handle
                return await self.target.click(self.options)
            elif isinstance(self.target, SelectorGroup):
                # Try each selector in the group
                return await self.target.execute(
                    lambda selector: self._click_selector(driver, selector, ctx)
                )
            else:
                # Convert string to Selector if needed
                selector = self.target if isinstance(self.target, Selector) else Selector(
                    type="css", value=self.target
                )
                return await self._click_selector(driver, selector, ctx)
                
        except Exception as e:
            logger.error(f"Error clicking on {self.target_desc}: {e}")
            return Error(e)
    
    async def _click_selector(
        self, driver: BrowserDriver, selector: Selector, context: ActionContext
    ) -> Result[None, Exception]:
        """Helper method to click an element found by selector"""
        try:
            # Use driver's click method which handles finding the element
            selector_value = selector.value
            
            # Handle different selector types
            if selector.type == "xpath":
                # Some drivers require special handling for XPath
                element_result = await driver.query_selector(selector_value)
                if element_result.is_error():
                    return element_result
                
                element = element_result.value
                if element is None:
                    return Error(Exception(f"Element not found: {selector}"))
                
                return await element.click(self.options)
            else:
                # Use CSS selector for standard case
                return await driver.click(selector_value, self.options)
        except Exception as e:
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
        options: Optional[ClickOptions] = None
    ):
        # Create options with click_count=2 if not specified
        if options is None:
            self.options = ClickOptions(click_count=2)
        else:
            # Update existing options to have click_count=2
            options_dict = options.model_dump() 
            options_dict['click_count'] = 2
            self.options = ClickOptions(**options_dict)
            
        self.target = target
        
        # Generate description for logging
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
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Double-click on the target element or coordinates"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Double-clicking on {self.target_desc}")
            
            # Use the Click action with click_count=2
            click_action = Click(self.target, self.options)
            return await click_action.execute(driver, ctx)
                
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
        options: Optional[MouseMoveOptions] = None
    ):
        self.button = button
        self.options = options or MouseMoveOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Press the specified mouse button"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Pressing {self.button} mouse button")
            return await driver.mouse_down(self.button)
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
        options: Optional[MouseMoveOptions] = None
    ):
        self.button = button
        self.options = options or MouseMoveOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Release the specified mouse button"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Releasing {self.button} mouse button")
            return await driver.mouse_up(self.button)
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
        options: Optional[DragOptions] = None
    ):
        self.source = source
        self.target = target
        self.options = options or DragOptions()
        
        # Generate description for logging
        def get_desc(item):
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
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Drag from source to target"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Dragging from {self.source_desc} to {self.target_desc}")
            
            # Convert source and target to the format expected by driver.drag
            source_resolved = await self._resolve_item(driver, self.source, ctx)
            if source_resolved.is_error():
                return source_resolved
            
            target_resolved = await self._resolve_item(driver, self.target, ctx)
            if target_resolved.is_error():
                return target_resolved
            
            return await driver.drag(
                source_resolved.value,
                target_resolved.value,
                self.options
            )
        except Exception as e:
            logger.error(f"Error dragging from {self.source_desc} to {self.target_desc}: {e}")
            return Error(e)
    
    async def _resolve_item(
        self, 
        driver: BrowserDriver, 
        item: Union[str, Selector, SelectorGroup, ElementHandle, CoordinateType],
        context: ActionContext
    ) -> Result[Union[str, ElementHandle, CoordinateType], Exception]:
        """Resolve a selector/group to the format expected by driver.drag"""
        try:
            if isinstance(item, tuple):
                # Already coordinates
                return Ok(item)
            elif isinstance(item, ElementHandle):
                # Already an element handle
                return Ok(item)
            elif isinstance(item, SelectorGroup):
                # Use first selector from group
                first_selector = item.selectors[0]
                return await self._resolve_item(driver, first_selector, context)
            elif isinstance(item, Selector):
                # Handle different selector types
                if item.type == "css":
                    return Ok(item.value)
                else:
                    # For non-CSS, resolve to element handle
                    element_result = await driver.query_selector(item.value)
                    if element_result.is_error():
                        return element_result
                    
                    element = element_result.value
                    if element is None:
                        return Error(Exception(f"Element not found: {item}"))
                    
                    return Ok(element)
            else:
                # Assume string is CSS selector
                return Ok(item)
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
        options: Optional[TypeOptions] = None
    ):
        self.target = target
        self.text = text
        self.options = options or TypeOptions()
        
        # Generate description for logging
        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Fill text into the target element"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Filling '{self.text}' into {self.target_desc}")
            
            if isinstance(self.target, ElementHandle):
                # Fill element handle
                return await self.target.fill(self.text, self.options)
            elif isinstance(self.target, SelectorGroup):
                # Try each selector in the group
                return await self.target.execute(
                    lambda selector: self._fill_selector(driver, selector, ctx)
                )
            else:
                # Convert string to Selector if needed
                selector = self.target if isinstance(self.target, Selector) else Selector(
                    type="css", value=self.target
                )
                return await self._fill_selector(driver, selector, ctx)
                
        except Exception as e:
            logger.error(f"Error filling text into {self.target_desc}: {e}")
            return Error(e)
    
    async def _fill_selector(
        self, driver: BrowserDriver, selector: Selector, context: ActionContext
    ) -> Result[None, Exception]:
        """Helper method to fill an element found by selector"""
        try:
            # Use driver's fill method which handles finding the element
            selector_value = selector.value
            
            # Handle different selector types
            if selector.type == "xpath":
                # Some drivers require special handling for XPath
                element_result = await driver.query_selector(selector_value)
                if element_result.is_error():
                    return element_result
                
                element = element_result.value
                if element is None:
                    return Error(Exception(f"Element not found: {selector}"))
                
                return await element.fill(self.text, self.options)
            else:
                # Use CSS selector for standard case
                return await driver.fill(selector_value, self.text, self.options)
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
        options: Optional[TypeOptions] = None
    ):
        # Use Fill action for implementation
        self.fill_action = Fill(target, text, options)
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Type text into the target element using Fill action"""
        return await self.fill_action.execute(driver, context)


class KeyPress(Action[None]):
    """
    Action to press a key or key combination
    
    Args:
        key: Key or key combination to press
        modifiers: List of keyboard modifiers to apply
    """
    
    def __init__(
        self,
        key: str,
        modifiers: List[KeyModifier] = None
    ):
        self.key = key
        self.modifiers = modifiers or []
        self.options = TypeOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Press key with optional modifiers"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Pressing key '{self.key}' with modifiers {[m.name for m in self.modifiers]}")
            
            # Apply modifiers if present
            for modifier in self.modifiers:
                await driver.key_down(modifier.name.lower())
            
            # Press the key
            result = await driver.key_press(self.key, self.options)
            
            # Release modifiers in reverse order
            for modifier in reversed(self.modifiers):
                await driver.key_up(modifier.name.lower())
                
            return result
        except Exception as e:
            logger.error(f"Error pressing key '{self.key}': {e}")
            return Error(e)

# todo KeyDown, KeyUp, Shortcut


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
        text: Optional[str] = None
    ):
        self.target = target
        self.value = value
        self.text = text
        
        if not value and not text:
            raise ValueError("Either value or text must be provided")
        
        # Generate description for logging
        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Select an option from the dropdown"""
        ctx = context or ActionContext()
        
        try:
            select_by = f"value='{self.value}'" if self.value else f"text='{self.text}'"
            logger.debug(f"Selecting option with {select_by} from {self.target_desc}")
            
            # Use JavaScript to select the option
            script = """
                const select = document.querySelector(arguments[0]);
                if (!select) return { success: false, error: 'Select element not found' };
                
                if (arguments[1]) {
                    // Select by value
                    const option = Array.from(select.options).find(opt => opt.value === arguments[1]);
                    if (option) {
                        option.selected = true;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        return { success: true };
                    } else {
                        return { success: false, error: 'Option with specified value not found' };
                    }
                } else if (arguments[2]) {
                    // Select by text
                    const option = Array.from(select.options).find(opt => opt.text === arguments[2]);
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
            
            if isinstance(self.target, ElementHandle):
                # For element handle, we need to find its selector
                # This is a workaround as we can't directly pass element handles to execute_script
                # in most browser drivers
                bbox_result = await self.target.get_bounding_box()
                if bbox_result.is_error():
                    return Error(Exception(f"Cannot get element position: {bbox_result.error}"))
                
                # Use JavaScript to find the element at this position and select from it
                complex_script = f"""
                    const elemFromPoint = document.elementFromPoint({bbox_result.value['x']}, {bbox_result.value['y']});
                    if (!elemFromPoint) return {{ success: false, error: 'Element not found at position' }};
                    
                    // Find the closest select element
                    const select = elemFromPoint.closest('select') || elemFromPoint;
                    if (select.tagName !== 'SELECT') return {{ success: false, error: 'Element is not a select' }};
                    
                    // Select by value or text
                    {script.split("const select = document.querySelector(arguments[0]);")[1]}
                """
                
                result = await driver.execute_script(
                    complex_script, 
                    None, 
                    self.value, 
                    self.text
                )
            elif isinstance(self.target, SelectorGroup):
                # Try each selector in the group
                for selector in self.target.selectors:
                    result = await driver.execute_script(
                        script, 
                        selector.value, 
                        self.value, 
                        self.text
                    )
                    
                    if result.is_error():
                        continue
                        
                    response = result.value
                    if response.get('success'):
                        return Ok(None)
                        
                return Error(Exception(f"Failed to select from any selector in group"))
            else:
                # Convert string to selector value if needed
                selector_value = self.target.value if isinstance(self.target, Selector) else self.target
                
                result = await driver.execute_script(
                    script, 
                    selector_value, 
                    self.value, 
                    self.text
                )
            
            if result.is_error():
                return result
                
            response = result.value
            if not response.get('success'):
                return Error(Exception(response.get('error', 'Failed to select option')))
                
            return Ok(None)
        except Exception as e:
            logger.error(f"Error selecting option from {self.target_desc}: {e}")
            return Error(e)