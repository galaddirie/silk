"""
Base browser driver interface that defines the contract for browser automation.
All browser implementations must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Awaitable, Callable, Dict, Generic, List, Optional, Protocol, 
    TypeVar, Union, cast, Mapping
)
from pathlib import Path
import logging
from expression.core import Result, Ok, Error
import asyncio

from silk.models.browser import (
    BrowserOptions, ElementHandle, 
    ClickOptions, TypeOptions, MouseMoveOptions, DragOptions,
    NavigationOptions, WaitOptions, ActionContext,
    MouseButtonLiteral, WaitStateLiteral, NavigationWaitLiteral,
    CoordinateType
)

T = TypeVar('T')
R = TypeVar('R')

logger = logging.getLogger(__name__)

class BrowserDriver(ABC, Generic[T]):
    """
    Abstract browser driver interface that defines the contract for browser automation.
    
    All concrete browser implementations (like Playwright, Selenium, etc.) must
    implement this interface to be usable with the Silk action system.
    """
    
    def __init__(self, options: BrowserOptions):
        """
        Initialize the browser driver with options
        
        Args:
            options: Configuration options for the browser
        """
        self.options = options
    
    @abstractmethod
    async def launch(self) -> Result[None, Exception]:
        """
        Launch the browser
        
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def close(self) -> Result[None, Exception]:
        """
        Close the browser
        
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def goto(
        self, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """
        Navigate to a URL
        
        Args:
            url: The URL to navigate to
            options: Optional navigation options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def current_url(self) -> Result[str, Exception]:
        """
        Get the current URL
        
        Returns:
            Result containing the current URL or an error
        """
        pass
    
    @abstractmethod
    async def get_page_source(self) -> Result[str, Exception]:
        """
        Get the current page HTML source
        
        Returns:
            Result containing the HTML source or an error
        """
        pass
    
    @abstractmethod
    async def take_screenshot(self, path: Path) -> Result[None, Exception]:
        """
        Take a screenshot and save it to the specified path
        
        Args:
            path: Path to save the screenshot
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """
        Query a single element with the provided selector
        
        Args:
            selector: CSS or XPath selector
            
        Returns:
            Result containing the element handle or None if not found
        """
        pass
    
    @abstractmethod
    async def query_selector_all(
        self, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        """
        Query all elements that match the provided selector
        
        Args:
            selector: CSS or XPath selector
            
        Returns:
            Result containing a list of element handles or an error
        """
        pass
    
    @abstractmethod
    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        """
        Execute JavaScript in the browser context
        
        Args:
            script: JavaScript code to execute
            args: Arguments to pass to the script
            
        Returns:
            Result containing the script result or an error
        """
        pass
    
    @abstractmethod
    async def wait_for_selector(
        self, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        """
        Wait for an element matching the selector to appear
        
        Args:
            selector: CSS or XPath selector
            options: Wait options including timeout, state, and poll interval
            
        Returns:
            Result containing the element handle or None if not found
        """
        pass
    
    @abstractmethod
    async def wait_for_navigation(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """
        Wait for navigation to complete
        
        Args:
            options: Navigation options including timeout and wait condition
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def mouse_move(
        self, x: int, y: int, options: Optional[MouseMoveOptions] = None
    ) -> Result[None, Exception]:
        """
        Move the mouse to the specified coordinates
        
        Args:
            x: X coordinate
            y: Y coordinate
            options: Mouse movement options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def mouse_move_to_element(
        self,
        element: ElementHandle,
        offset_x: int = 0,
        offset_y: int = 0,
        options: Optional[MouseMoveOptions] = None,
    ) -> Result[None, Exception]:
        """
        Move the mouse to the specified element with optional offset
        
        Args:
            element: Target element
            offset_x: X offset from the element's top-left corner
            offset_y: Y offset from the element's top-left corner
            options: Mouse movement options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def click(
        self, selector: str, options: Optional[ClickOptions] = None
    ) -> Result[None, Exception]:
        """
        Click an element
        
        Args:
            selector: CSS or XPath selector
            options: Click options (button, count, delay, etc.)
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def double_click(
        self, selector: str, options: Optional[ClickOptions] = None
    ) -> Result[None, Exception]:
        """
        Double click an element
        
        Args:
            selector: CSS or XPath selector
            options: Click options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def mouse_down(
        self, button: MouseButtonLiteral = "left"
    ) -> Result[None, Exception]:
        """
        Press a mouse button
        
        Args:
            button: Mouse button to press
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def mouse_up(
        self, button: MouseButtonLiteral = "left"
    ) -> Result[None, Exception]:
        """
        Release a mouse button
        
        Args:
            button: Mouse button to release
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """
        Press a key or key combination
        
        Args:
            key: Key to press
            options: Key press options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def key_down(self, key: str) -> Result[None, Exception]:
        """
        Press and hold a key
        
        Args:
            key: Key to press
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def key_up(self, key: str) -> Result[None, Exception]:
        """
        Release a key
        
        Args:
            key: Key to release
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def fill(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """
        Fill an input element with text
        
        Args:
            selector: CSS or XPath selector
            text: Text to fill
            options: Fill options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    @abstractmethod
    async def drag(
        self,
        source: Union[str, ElementHandle, CoordinateType],
        target: Union[str, ElementHandle, CoordinateType],
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """
        Drag from one element or position to another
        
        Args:
            source: Source selector, element, or coordinates
            target: Target selector, element, or coordinates
            options: Drag options
            
        Returns:
            Result indicating success or failure
        """
        pass
    
    # Utility methods
    async def get_text_from_selector(self, selector: str) -> Result[str, Exception]:
        """
        Get text from an element matching the selector
        
        Args:
            selector: CSS or XPath selector
            
        Returns:
            Result containing the text or an error
        """
        try:
            # Find element
            element_result = await self.query_selector(selector)
            if element_result.is_error():
                return Error(Exception(f"Failed to find element: {selector}"))
            
            element = element_result.value
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))
            
            # Get text
            return await element.get_text()
        except Exception as e:
            logger.error(f"Error getting text from {selector}: {e}")
            return Error(e)
    
    async def click_selector(self, selector: str, options: Optional[ClickOptions] = None) -> Result[None, Exception]:
        """
        Click an element matching the selector
        
        Args:
            selector: CSS or XPath selector
            options: Click options
            
        Returns:
            Result indicating success or failure
        """
        try:
            # Use the driver's built-in click method
            return await self.click(selector, options)
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {e}")
            return Error(e)
    
    async def with_timeout(
        self, action: Callable[['BrowserDriver'], Awaitable[Result[R, Exception]]], 
        timeout_ms: int
    ) -> Result[R, Exception]:
        """
        Execute an action with a timeout
        
        Args:
            action: Function that takes a driver and returns a Result
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Result from the action or timeout error
        """
        try:
            # Run the action with a timeout
            result = await asyncio.wait_for(
                action(self),
                timeout=timeout_ms / 1000  # Convert to seconds
            )
            
            # Return the result
            if isinstance(result, Result):
                return result
            else:
                # This should not happen with proper typing
                return Error(Exception(f"Action did not return a Result: {result}"))
        except asyncio.TimeoutError:
            logger.warning(f"Operation timed out after {timeout_ms}ms")
            return Error(Exception(f"Operation timed out after {timeout_ms}ms"))
        except Exception as e:
            logger.error(f"Error executing action with timeout: {e}")
            return Error(e)