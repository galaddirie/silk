"""
Actions for creating and managing multiple browser contexts and pages.
"""

from typing import Dict, List, Optional, Any, TypeVar, Union, Generic, cast
import asyncio
import logging

from expression.core import Result, Ok, Error

from silk.models.browser import ActionContext
from silk.browsers.driver import BrowserDriver
from silk.actions.base import Action

T = TypeVar('T')
logger = logging.getLogger(__name__)


class CreateContext(Action[str]):
    """
    Action to create a new browser context
    
    Args:
        context_id: Optional ID for the context
        options: Additional context options
        create_page: Whether to automatically create a page
        
    Returns:
        The context ID
    """
    
    def __init__(
        self,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        create_page: bool = True
    ):
        self.context_id = context_id
        self.options = options
        self.create_page = create_page
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Create a new browser context"""
        ctx = context or ActionContext()
        
        try:
            # Get the browser manager from the driver
            browser_manager = getattr(driver, "browser_manager", None)
            if not browser_manager:
                return Error(Exception("Driver does not support browser manager"))
            
            # Create the context
            result = await browser_manager.create_context(
                context_id=self.context_id,
                options=self.options,
                create_page=self.create_page
            )
            
            if result.is_error():
                return Error(result.error)
            
            # Store new context ID in action context for subsequent actions
            if ctx:
                ctx.browser_context_id = result.value.id
                
                # Store default page ID if one was created
                if self.create_page and result.value.default_page_id:
                    ctx.page_id = result.value.default_page_id
            
            return Ok(result.value.id)
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)


class CreatePage(Action[str]):
    """
    Action to create a new page in a context
    
    Args:
        page_id: Optional ID for the page
        context_id: Optional context ID (uses current context if not specified)
        
    Returns:
        The page ID
    """
    
    def __init__(
        self,
        page_id: Optional[str] = None,
        context_id: Optional[str] = None
    ):
        self.page_id = page_id
        self.context_id = context_id
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Create a new page in a context"""
        ctx = context or ActionContext()
        
        try:
            # Get the browser manager from the driver
            browser_manager = getattr(driver, "browser_manager", None)
            if not browser_manager:
                return Error(Exception("Driver does not support browser manager"))
            
            # Get the browser context
            context_id = self.context_id or ctx.browser_context_id
            context_result = browser_manager.get_context(context_id)
            
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.value
            
            # Create the page
            page_result = await browser_context.create_page(self.page_id)
            
            if page_result.is_error():
                return Error(page_result.error)
            
            # Set as current page in action context
            if ctx:
                ctx.page_id = page_result.value.id
                
                # Ensure context ID is also set
                if not ctx.browser_context_id:
                    ctx.browser_context_id = browser_context.id
            
            return Ok(page_result.value.id)
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return Error(e)


class SwitchContext(Action[None]):
    """
    Action to switch the current browser context
    
    Args:
        context_id: ID of the context to switch to
    """
    
    def __init__(self, context_id: str):
        self.context_id = context_id
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Switch the current browser context"""
        ctx = context or ActionContext()
        
        try:
            # Get the browser manager from the driver
            browser_manager = getattr(driver, "browser_manager", None)
            if not browser_manager:
                return Error(Exception("Driver does not support browser manager"))
            
            # Check if the context exists
            context_result = browser_manager.get_context(self.context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            # Update the action context
            if ctx:
                ctx.browser_context_id = self.context_id
                
                # Clear page ID to use default page in new context
                browser_context = context_result.value
                ctx.page_id = browser_context.default_page_id
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error switching context: {e}")
            return Error(e)


class SwitchPage(Action[None]):
    """
    Action to switch the current page
    
    Args:
        page_id: ID of the page to switch to
        context_id: Optional context ID (uses current context if not specified)
    """
    
    def __init__(
        self,
        page_id: str,
        context_id: Optional[str] = None
    ):
        self.page_id = page_id
        self.context_id = context_id
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[None, Exception]:
        """Switch the current page"""
        ctx = context or ActionContext()
        
        try:
            # Get the browser manager from the driver
            browser_manager = getattr(driver, "browser_manager", None)
            if not browser_manager:
                return Error(Exception("Driver does not support browser manager"))
            
            # Get the browser context
            context_id = self.context_id or ctx.browser_context_id
            context_result = browser_manager.get_context(context_id)
            
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.value
            
            # Check if the page exists
            page_result = browser_context.get_page(self.page_id)
            if page_result.is_error():
                return Error(page_result.error)
            
            # Update the action context
            if ctx:
                ctx.page_id = self.page_id
                
                # Ensure context ID is also set
                if not ctx.browser_context_id:
                    ctx.browser_context_id = browser_context.id
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error switching page: {e}")
            return Error(e)


class WithPage(Generic[T], Action[T]):
    """
    Action to execute another action in a specific page
    
    Args:
        action: The action to execute
        page_id: ID of the page to use
        context_id: Optional context ID (uses current context if not specified)
        
    Returns:
        The result of the action
    """
    
    def __init__(
        self,
        action: Action[T],
        page_id: str,
        context_id: Optional[str] = None
    ):
        self.action = action
        self.page_id = page_id
        self.context_id = context_id
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
        """Execute an action in a specific page"""
        ctx = context or ActionContext()
        
        try:
            # Create a new action context with the target page and context
            new_ctx = ActionContext(
                retry_count=ctx.retry_count,
                max_retries=ctx.max_retries,
                retry_delay_ms=ctx.retry_delay_ms,
                timeout_ms=ctx.timeout_ms,
                parent_context=ctx,
                metadata=ctx.metadata.copy(),
                browser_context_id=self.context_id or ctx.browser_context_id,
                page_id=self.page_id
            )
            
            # Execute the action with the new context
            return await self.action.execute(driver, new_ctx)
        except Exception as e:
            logger.error(f"Error executing action in page {self.page_id}: {e}")
            return Error(e)


class WithContext(Generic[T], Action[T]):
    """
    Action to execute another action in a specific browser context
    
    Args:
        action: The action to execute
        context_id: ID of the context to use
        
    Returns:
        The result of the action
    """
    
    def __init__(
        self,
        action: Action[T],
        context_id: str
    ):
        self.action = action
        self.context_id = context_id
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[T, Exception]:
        """Execute an action in a specific browser context"""
        ctx = context or ActionContext()
        
        try:
            # Get the browser manager to find default page
            browser_manager = getattr(driver, "browser_manager", None)
            if not browser_manager:
                return Error(Exception("Driver does not support browser manager"))
                
            # Get default page ID from context
            context_result = browser_manager.get_context(self.context_id)
            if context_result.is_error():
                return Error(context_result.error)
                
            browser_context = context_result.value
            
            # Create a new action context with the target context
            new_ctx = ActionContext(
                retry_count=ctx.retry_count,
                max_retries=ctx.max_retries,
                retry_delay_ms=ctx.retry_delay_ms,
                timeout_ms=ctx.timeout_ms,
                parent_context=ctx,
                metadata=ctx.metadata.copy(),
                browser_context_id=self.context_id,
                page_id=browser_context.default_page_id
            )
            
            # Execute the action with the new context
            return await self.action.execute(driver, new_ctx)
        except Exception as e:
            logger.error(f"Error executing action in context {self.context_id}: {e}")
            return Error(e)

