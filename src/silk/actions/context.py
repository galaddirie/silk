from typing import Optional, Dict, Any, TypeVar, Generic, Tuple
import logging

from expression.core import Result, Ok, Error

from silk.models.browser import ActionContext
from silk.actions.base import Action
from silk.browsers.context import BrowserContext, BrowserPage

T = TypeVar('T')
logger = logging.getLogger(__name__)

class CreateContext(Action[BrowserContext]):
    """
    Create a new browser context
    
    Args:
        nickname: Optional nickname for the context
        options: Optional context creation options
        create_page: Whether to create a default page in the context
    """
    
    def __init__(
        self, 
        nickname: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        create_page: bool = True
    ):
        self.nickname = nickname
        self.options = options
        self.create_page = create_page
    
    async def execute(self, context: ActionContext) -> Result[BrowserContext, Exception]:
        """Create a new browser context"""
        if not context.browser_manager:
            return Error(Exception("Browser manager is required"))
        
        try:
            return await context.browser_manager.create_context(
                nickname=self.nickname,
                options=self.options,
                create_page=self.create_page
            )
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)


class SwitchContext(Action[None]):
    """
    Switch the active context in the current ActionContext
    
    Args:
        context_id_or_nickname: ID or nickname of the context to switch to
    """
    
    def __init__(self, context_id_or_nickname: str):
        self.context_id_or_nickname = context_id_or_nickname
    
    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Switch to a different context"""
        if not context.browser_manager:
            return Error(Exception("Browser manager is required"))
        
        try:
            # Get the target context
            context_result = context.browser_manager.get_context(self.context_id_or_nickname)
            if context_result.is_error():
                return Error(context_result.error)
            
            # Update the context ID in the ActionContext
            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))
                
            context.context_id = browser_context.id
            
            # If the target context has a default page, set that as the active page
            if browser_context.default_page_id:
                context.page_id = browser_context.default_page_id
            else:
                context.page_id = None
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error switching context: {e}")
            return Error(e)


class CreatePage(Action[BrowserPage]):
    """
    Create a new page in the current context
    
    Args:
        nickname: Optional nickname for the page
    """
    
    def __init__(self, nickname: Optional[str] = None):
        self.nickname = nickname
    
    async def execute(self, context: ActionContext) -> Result[BrowserPage, Exception]:
        """Create a new page"""
        if not context.browser_manager or not context.context_id:
            return Error(Exception("Browser manager and context ID are required"))
        
        try:
            # Get the current context
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))
            
            # Create a new page
            page_result = await browser_context.create_page(nickname=self.nickname)
            if page_result.is_error():
                return Error(page_result.error)
            
            # Set this as the active page
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to create page"))
                
            context.page_id = page.id
            
            return page_result
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return Error(e)


class SwitchPage(Action[None]):
    """
    Switch the active page in the current context
    
    Args:
        page_id_or_nickname: ID or nickname of the page to switch to
    """
    
    def __init__(self, page_id_or_nickname: str):
        self.page_id_or_nickname = page_id_or_nickname
    
    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Switch to a different page"""
        if not context.browser_manager or not context.context_id:
            return Error(Exception("Browser manager and context ID are required"))
        
        try:
            # Get the current context
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))
            
            # Find the page
            page_result = browser_context.get_page(self.page_id_or_nickname)
            if page_result.is_error():
                # If page isn't found in current context, we just return the error
                # since we don't have a way to look up pages by nickname across contexts
                return Error(page_result.error)
            
            # Set this as the active page
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))
                
            context.page_id = page.id
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error switching page: {e}")
            return Error(e)


class CloseContext(Action[None]):
    """
    Close a context and all its pages
    
    Args:
        context_id_or_nickname: ID or nickname of the context to close,
                              or None to close the current context
    """
    
    def __init__(self, context_id_or_nickname: Optional[str] = None):
        self.context_id_or_nickname = context_id_or_nickname
    
    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Close a context"""
        if not context.browser_manager:
            return Error(Exception("Browser manager is required"))
        
        try:
            # Use current context if none specified
            target_context_id = self.context_id_or_nickname or context.context_id
            if not target_context_id:
                return Error(Exception("No context specified to close"))
            
            # Close the context
            close_result = await context.browser_manager.close_context(target_context_id)
            if close_result.is_error():
                return Error(close_result.error)
            
            # If we closed the current context, reset context_id and page_id
            if context.context_id == target_context_id:
                context.context_id = None
                context.page_id = None
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing context: {e}")
            return Error(e)


class ClosePage(Action[None]):
    """
    Close a page
    
    Args:
        page_id_or_nickname: ID or nickname of the page to close,
                           or None to close the current page
    """
    
    def __init__(self, page_id_or_nickname: Optional[str] = None):
        self.page_id_or_nickname = page_id_or_nickname
    
    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        """Close a page"""
        if not context.browser_manager or not context.context_id:
            return Error(Exception("Browser manager and context ID are required"))
        
        try:
            # Get the current context
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))
            
            # Use current page if none specified
            target_page_id = self.page_id_or_nickname or context.page_id
            if not target_page_id:
                return Error(Exception("No page specified to close"))
            
            # Get the page
            page_result = browser_context.get_page(target_page_id)
            if page_result.is_error():
                return Error(page_result.error)
            
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))
            
            # Close the page
            close_result = await page.close()
            if close_result.is_error():
                return Error(close_result.error)
            
            # If we closed the current page, reset page_id
            if context.page_id == page.id:
                context.page_id = browser_context.default_page_id
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)