# browser/driver.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Protocol, Callable, TypeVar, Generic, Awaitable
from pydantic import BaseModel, Field
from expression import pipe, curry, compose
from expression.core import Result, Option
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
        return await pipe(
            await self.query_selector(selector),
            lambda result: result.bind(
                lambda element: element.get_text() if element else Result.failure(Exception(f"Element not found: {selector}"))
            )
        )
    
    async def click_selector(self, selector: str) -> Result[None, Exception]:
        """
        Click an element matching the selector
        
        Args:
            selector: CSS selector to find the element
            
        Returns:
            Result indicating success or failure
        """
        return await pipe(
            await self.query_selector(selector),
            lambda result: result.bind(
                lambda element: element.click() if element else Result.failure(Exception(f"Element not found: {selector}"))
            )
        )
    
    async def type_in_selector(self, selector: str, text: str) -> Result[None, Exception]:
        """
        Type text into an element matching the selector
        
        Args:
            selector: CSS selector to find the element
            text: Text to type
            
        Returns:
            Result indicating success or failure
        """
        return await pipe(
            await self.query_selector(selector),
            lambda result: result.bind(
                lambda element: element.type(text) if element else Result.failure(Exception(f"Element not found: {selector}"))
            )
        )
    
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
            return result
        except asyncio.TimeoutError:
            return Result.failure(Exception(f"Operation timed out after {timeout_ms}ms"))
        except Exception as e:
            return Result.failure(e)

