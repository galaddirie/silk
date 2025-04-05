# browser/driver.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Protocol, Callable, TypeVar, Generic, Awaitable, Literal
from pydantic import BaseModel, Field
from expression import pipe, curry, compose
from expression.core import Result, Option, Error
from expression.collections import seq
from pathlib import Path
import asyncio

T = TypeVar('T')
S = TypeVar('S')
R = TypeVar('R')

class ElementHandle(Protocol):
    """Protocol defining the interface for browser element handles"""
    
    @abstractmethod
    async def click(self) -> Result[None, Exception]:
        """Click the element"""
        pass
    
    @abstractmethod
    async def type(self, text: str) -> Result[None, Exception]:
        """Type text into the element"""
        pass
    
    @abstractmethod
    async def get_text(self) -> Result[str, Exception]:
        """Get the text content of the element"""
        pass
    
    @abstractmethod
    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        """Get attribute value from the element"""
        pass
    
    @abstractmethod
    async def is_visible(self) -> Result[bool, Exception]:
        """Check if the element is visible"""
        pass


class BrowserOptions(BaseModel):
    """Configuration options for browser instances"""
    
    headless: bool = True
    timeout: int = 30000  # milliseconds
    viewport_width: int = 1366
    viewport_height: int = 768
    proxy: Optional[str] = None
    extra_args: Dict[str, Any] = Field(default_factory=dict)


class BrowserDriver(ABC, Generic[T]):
    """Abstract browser driver interface"""
    
    def __init__(self, options: BrowserOptions):
        self.options = options
    
    @abstractmethod
    async def launch(self) -> Result[None, Exception]:
        """Launch the browser"""
        pass
    
    @abstractmethod
    async def close(self) -> Result[None, Exception]:
        """Close the browser"""
        pass
    
    @abstractmethod
    async def goto(self, url: str) -> Result[None, Exception]:
        """Navigate to a URL"""
        pass
    
    @abstractmethod
    async def current_url(self) -> Result[str, Exception]:
        """Get the current URL"""
        pass
    
    @abstractmethod
    async def get_page_source(self) -> Result[str, Exception]:
        """Get the current page HTML source"""
        pass
    
    @abstractmethod
    async def take_screenshot(self, path: Path) -> Result[None, Exception]:
        """Take a screenshot and save it to the specified path"""
        pass
    
    @abstractmethod
    async def query_selector(self, selector: str) -> Result[Optional[T], Exception]:
        """Query a single element with the provided selector"""
        pass
    
    @abstractmethod
    async def query_selector_all(self, selector: str) -> Result[List[T], Exception]:
        """Query all elements that match the provided selector"""
        pass
    
    @abstractmethod
    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        """Execute JavaScript in the browser context"""
        pass
    
    @abstractmethod
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Result[Optional[T], Exception]:
        """Wait for an element matching the selector to appear"""
        pass
    
    @abstractmethod
    async def wait_for_navigation(self, timeout: Optional[int] = None) -> Result[None, Exception]:
        """Wait for navigation to complete"""
        pass
    
    @abstractmethod
    async def mouse_move(self, x: int, y: int) -> Result[None, Exception]:
        """Move the mouse to the specified coordinates"""
        pass
    
    @abstractmethod
    async def mouse_move_to_element(self, element: T, offset_x: int = 0, offset_y: int = 0) -> Result[None, Exception]:
        """Move the mouse to the specified element with optional offset"""
        pass
    
    @abstractmethod
    async def mouse_down(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        """Press a mouse button"""
        pass
    
    @abstractmethod
    async def mouse_up(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        """Release a mouse button"""
        pass
    
    @abstractmethod
    async def mouse_click(self, button: Literal["left", "right", "middle"] = "left", click_count: int = 1, delay_between_ms: Optional[int] = None) -> Result[None, Exception]:
        """Click a mouse button"""
        pass
    
    @abstractmethod
    async def mouse_double_click(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        """Double click a mouse button"""
        pass
    
    @abstractmethod
    async def press(self, key: str) -> Result[None, Exception]:
        """Press a key or key combination"""
        pass
    
    @abstractmethod
    async def key_down(self, key: str) -> Result[None, Exception]:
        """Press and hold a key"""
        pass
    
    @abstractmethod
    async def key_up(self, key: str) -> Result[None, Exception]:
        """Release a key"""
        pass
    
    @abstractmethod
    async def type(self, text: str, delay: Optional[float] = None) -> Result[None, Exception]:
        """Type a sequence of characters with optional delay between keystrokes"""
        pass
    
    def pipe(self, f: Callable[['BrowserDriver[T]'], S]) -> S:
        """Pipe the browser driver through a function"""
        return f(self)
    
    # Helper methods for common compositions
    
    async def get_text_from_selector(self, selector: str) -> Result[str, Exception]:
        """
        Get text from an element matching the selector
        
        Args:
            selector: CSS selector to find the element
            
        Returns:
            Result containing the text or an exception
        """
        result = await self.query_selector(selector)
        if result.is_error():
            return Error(Exception(f"Failed to query selector: {selector}"))
            
        # Cast to avoid type errors
        element: Optional[ElementHandle] = None
        if result.is_ok():
            value = getattr(result, 'value', None)
            element = value
            
        if not element:
            return Error(Exception(f"Element not found: {selector}"))
            
        return await element.get_text()
    
    async def click_selector(self, selector: str) -> Result[None, Exception]:
        """
        Click an element matching the selector
        
        Args:
            selector: CSS selector to find the element
            
        Returns:
            Result indicating success or failure
        """
        result = await self.query_selector(selector)
        if result.is_error():
            return Error(Exception(f"Failed to query selector: {selector}"))
            
        # Cast to avoid type errors
        element: Optional[ElementHandle] = None
        if result.is_ok():
            value = getattr(result, 'value', None)
            element = value
            
        if not element:
            return Error(Exception(f"Element not found: {selector}"))
            
        return await element.click()
    
    async def type_in_selector(self, selector: str, text: str) -> Result[None, Exception]:
        """
        Type text into an element matching the selector
        
        Args:
            selector: CSS selector to find the element
            text: Text to type
            
        Returns:
            Result indicating success or failure
        """
        result = await self.query_selector(selector)
        if result.is_error():
            return Error(Exception(f"Failed to query selector: {selector}"))
            
        # Cast to avoid type errors
        element: Optional[ElementHandle] = None
        if result.is_ok():
            value = getattr(result, 'value', None)
            element = value
            
        if not element:
            return Error(Exception(f"Element not found: {selector}"))
            
        return await element.type(text)
    
    async def with_timeout(self, action: Callable[['BrowserDriver[T]'], Awaitable[Result[R, Exception]]], 
                         timeout_ms: int) -> Result[R, Exception]:
        """
        Execute an action with a timeout
        
        Args:
            action: Function that takes a driver and returns a Result
            timeout_ms: Timeout in milliseconds
            
        Returns:
            Result from the action or timeout error
        """
        try:
            result = await asyncio.wait_for(
                action(self),
                timeout=timeout_ms / 1000
            )
            if isinstance(result, Result):
                return result
            else:
                # This should not happen if the action function is correctly typed
                return Error(Exception(f"Action did not return a Result: {result}"))
        except asyncio.TimeoutError:
            return Error(Exception(f"Operation timed out after {timeout_ms}ms"))
        except Exception as e:
            return Error(e)

