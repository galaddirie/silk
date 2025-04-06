"""
Navigation actions for browser movement, waiting for elements, and capturing screenshots.
"""

from typing import Optional, Union, Tuple, List, Dict, Any, Callable
from pathlib import Path
from expression.core import Result, Ok, Error
import logging
import asyncio

from silk.browsers.driver import BrowserDriver
from silk.models.browser import (
    NavigationOptions, WaitOptions, 
    WaitStateLiteral, NavigationWaitLiteral, ActionContext
)
from silk.actions.base import Action
from silk.selectors.selector import Selector, SelectorGroup

logger = logging.getLogger(__name__)


class Navigate(Action[None]):
    """
    Action to navigate to a URL
    
    Args:
        url: URL to navigate to
        options: Additional navigation options
    """
    
    def __init__(
        self,
        url: str,
        options: Optional[NavigationOptions] = None
    ):
        self.url = url
        self.options = options or NavigationOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Navigate to the specified URL"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Navigating to {self.url}")
            return await driver.goto(self.url, self.options)
        except Exception as e:
            logger.error(f"Error navigating to {self.url}: {e}")
            return Error(e)


class GoBack(Action[None]):
    """
    Action to navigate back in browser history
    
    Args:
        options: Additional navigation options
    """
    
    def __init__(
        self,
        options: Optional[NavigationOptions] = None
    ):
        self.options = options or NavigationOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Navigate back in browser history"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Navigating back in history")
            
            # Execute JavaScript for more reliable navigation
            script = """
                window.history.back();
                return true;
            """
            
            result = await driver.execute_script(script)
            if result.is_error():
                return result
            
            # Wait for navigation to complete
            return await driver.wait_for_navigation(self.options)
        except Exception as e:
            logger.error(f"Error navigating back: {e}")
            return Error(e)


class GoForward(Action[None]):
    """
    Action to navigate forward in browser history
    
    Args:
        options: Additional navigation options
    """
    
    def __init__(
        self,
        options: Optional[NavigationOptions] = None
    ):
        self.options = options or NavigationOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Navigate forward in browser history"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Navigating forward in history")
            
            # Execute JavaScript for more reliable navigation
            script = """
                window.history.forward();
                return true;
            """
            
            result = await driver.execute_script(script)
            if result.is_error():
                return result
            
            # Wait for navigation to complete
            return await driver.wait_for_navigation(self.options)
        except Exception as e:
            logger.error(f"Error navigating forward: {e}")
            return Error(e)


class Reload(Action[None]):
    """
    Action to reload the current page
    
    Args:
        options: Additional navigation options
    """
    
    def __init__(
        self,
        options: Optional[NavigationOptions] = None
    ):
        self.options = options or NavigationOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Reload the current page"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Reloading page")
            
            # Execute JavaScript for more reliable reload
            script = """
                window.location.reload();
                return true;
            """
            
            result = await driver.execute_script(script)
            if result.is_error():
                return result
            
            # Wait for navigation to complete
            return await driver.wait_for_navigation(self.options)
        except Exception as e:
            logger.error(f"Error reloading page: {e}")
            return Error(e)


class WaitForSelector(Action[Any]):
    """
    Action to wait for an element to appear in the DOM
    
    Args:
        selector: Element selector to wait for
        options: Additional wait options
        
    Returns:
        The found element if successful
    """
    
    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup],
        options: Optional[WaitOptions] = None
    ):
        self.selector = selector
        self.options = options or WaitOptions()
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
        """Wait for selector to match an element in the DOM"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Waiting for selector {self.selector_desc}")
            
            if isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                for selector in self.selector.selectors:
                    try:
                        result = await self._wait_for_selector(driver, selector)
                        if result.is_ok():
                            return result
                    except Exception:
                        # Continue to next selector
                        pass
                        
                return Error(Exception(f"No selector in group matched: {self.selector.name}"))
            else:
                # Convert string to Selector if needed
                selector = self.selector if isinstance(self.selector, Selector) else Selector(
                    type="css", value=self.selector
                )
                return await self._wait_for_selector(driver, selector)
                
        except Exception as e:
            logger.error(f"Error waiting for selector {self.selector_desc}: {e}")
            return Error(e)
    
    async def _wait_for_selector(self, driver: BrowserDriver, selector: Selector) -> Result[Any, Exception]:
        """Helper method to wait for a specific selector"""
        try:
            # Get timeout from options or selector
            timeout = self.options.timeout or selector.timeout
            
            # Use driver's wait_for_selector method
            return await driver.wait_for_selector(
                selector.value, 
                self._create_driver_options(timeout)
            )
        except Exception as e:
            return Error(e)
    
    def _create_driver_options(self, timeout: Optional[int]) -> WaitOptions:
        """Create options object with the right timeout"""
        options_dict = self.options.model_dump() if hasattr(self.options, "model_dump") else self.options.dict()
        if timeout is not None:
            options_dict["timeout"] = timeout
        return WaitOptions(**options_dict)


class WaitForNavigation(Action[None]):
    """
    Action to wait for a navigation to complete
    
    Args:
        options: Additional navigation options
    """
    
    def __init__(
        self,
        options: Optional[NavigationOptions] = None
    ):
        self.options = options or NavigationOptions()
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Wait for navigation to complete"""
        ctx = context or ActionContext()
        
        try:
            wait_until = self.options.wait_until
            logger.debug(f"Waiting for navigation to complete (wait_until={wait_until})")
            
            return await driver.wait_for_navigation(self.options)
        except Exception as e:
            logger.error(f"Error waiting for navigation: {e}")
            return Error(e)


class WaitForFunction(Action[Any]):
    """
    Action to wait for a JavaScript function to return true
    
    Args:
        function_body: JavaScript function body or expression that evaluates to true/false
        polling: Polling interval in milliseconds
        timeout: Timeout in milliseconds
        
    Returns:
        The return value of the function when it evaluates to true
    """
    
    def __init__(
        self,
        function_body: str,
        polling: int = 100,
        timeout: int = 30000
    ):
        self.function_body = function_body
        self.polling = polling
        self.timeout = timeout
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
        """Wait for function to evaluate to true"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Waiting for function to return true (timeout={self.timeout}ms)")
            
            # Handle both expression and function body formats
            is_expression = not self.function_body.strip().startswith("function") and "{" not in self.function_body
            
            if is_expression:
                # Wrap expression in a function
                script = f"return () => {self.function_body};"
            else:
                # Use as-is if it's already a function
                script = f"return {self.function_body};"
            
            # First get the function
            func_result = await driver.execute_script(script)
            if func_result.is_error():
                return func_result
            
            # Now repeatedly execute until it returns true or timeout
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check if we've exceeded timeout
                current_time = asyncio.get_event_loop().time()
                if (current_time - start_time) * 1000 > self.timeout:
                    return Error(Exception(f"Wait for function timed out after {self.timeout}ms"))
                
                # Execute the function
                result = await driver.execute_script("return (arguments[0])();")
                if result.is_error():
                    return result
                
                # If result is truthy, we're done
                if result.value:
                    return result
                
                # Wait before polling again
                await asyncio.sleep(self.polling / 1000)
                
        except Exception as e:
            logger.error(f"Error waiting for function: {e}")
            return Error(e)


class Screenshot(Action[Path]):
    """
    Action to take a screenshot
    
    Args:
        path: Path where to save the screenshot
        
    Returns:
        The path to the saved screenshot
    """
    
    def __init__(self, path: Path):
        self.path = path
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Path, Exception]:
        """Take a screenshot and save it to the specified path"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Taking screenshot and saving to {self.path}")
            
            # Ensure directory exists
            self.path.parent.mkdir(parents=True, exist_ok=True)
            
            result = await driver.take_screenshot(self.path)
            if result.is_error():
                return result
            
            return Ok(self.path)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return Error(e)


class GetCurrentUrl(Action[str]):
    """
    Action to get the current URL
    
    Returns:
        The current URL
    """
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Get the current URL"""
        ctx = context or ActionContext()
        
        try:
            logger.debug("Getting current URL")
            return await driver.current_url()
        except Exception as e:
            logger.error(f"Error getting current URL: {e}")
            return Error(e)


class GetPageSource(Action[str]):
    """
    Action to get the page source
    
    Returns:
        The HTML source of the current page
    """
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Get the HTML source of the current page"""
        ctx = context or ActionContext()
        
        try:
            logger.debug("Getting page source")
            return await driver.get_page_source()
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return Error(e)


class ExecuteScript(Action[Any]):
    """
    Action to execute JavaScript in the browser
    
    Args:
        script: JavaScript code to execute
        args: Arguments to pass to the script
        
    Returns:
        The return value of the script
    """
    
    def __init__(self, script: str, *args: Any):
        self.script = script
        self.args = args
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
        """Execute JavaScript code in the browser"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Executing script: {self.script[:50]}...")
            return await driver.execute_script(self.script, *self.args)
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return Error(e)