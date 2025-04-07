from typing import Dict, List, Optional, Any, Union, cast, Callable, TypeVar, TYPE_CHECKING, AsyncIterator
from pathlib import Path
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from expression.core import Result, Ok, Error

from silk.browsers.driver import BrowserDriver
from silk.browsers.driver_factory import create_driver, ValidDriverTypes
from silk.models.browser import BrowserOptions, ActionContext
from silk.actions.base import Action
from silk.browsers.context import BrowserContext  # Added missing import


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

T = TypeVar("T")

class BrowserManager:
    """
    Manages multiple browser contexts and their pages for parallel and sequential execution.
    Acts as the main entry point for executing actions.
    """
    
    def __init__(self, driver_type: Optional[ValidDriverTypes] = 'playwright', default_options: Optional[BrowserOptions] = None):
        """
        Initialize the browser manager
        
        Args:
            driver_type: The type of driver to use. Valid values are 'playwright', 'selenium', 'puppeteer'. Defaults to 'playwright'
            default_options: Default browser options
        """
        self.default_options = default_options or BrowserOptions()  # Fixed: Initialize with default instance
        self.drivers: Dict[str, BrowserDriver] = {}
        self.contexts: Dict[str, 'BrowserContext'] = {}
        self.default_context_id: Optional[str] = None
        self.driver_type = driver_type
        
    async def __aenter__(self) -> 'BrowserManager':
        """Allow usage as async context manager"""
        return self
        
    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        """Clean up when exiting the context manager"""
        await self.close_all()
    
    async def create_context(
        self, 
        nickname: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        create_page: bool = True
    ) -> Result['BrowserContext', Exception]:
        """Create a new browser context"""
        try:
            context_id = nickname or f"context-{len(self.contexts) + 1}"
            
            if context_id in self.contexts:
                return Error(Exception(f"Context with ID '{context_id}' already exists"))
            
            if context_id not in self.drivers:
                # Make sure driver_type is not None
                driver_type = self.driver_type or 'playwright'
                driver = create_driver(driver_type, self.default_options)
                
                # Fixed: Always await launch_result
                launch_result = await driver.launch()
                
                if launch_result.is_error():
                    return Error(launch_result.error)
                
                self.drivers[context_id] = driver
            else:
                driver = self.drivers[context_id]
            
            # Fixed: Always await context_result
            context_result = await driver.create_context(options)
            
            if context_result.is_error():
                return Error(context_result.error)
            
            context_ref = context_result.default_value(None)
            
            if context_ref is None:
                return Error(Exception("Failed to create context"))
            
            context = BrowserContext(
                context_id=context_id,
                driver=driver,
                manager=self,
                options=options,
                context_ref=context_ref
            )
            
            self.contexts[context_id] = context
            
            if self.default_context_id is None:
                self.default_context_id = context_id
            
            if create_page:
                # Fixed: Always await page_result
                page_result = await context.create_page()
                
                if page_result.is_error():
                    return Error(page_result.error)
            
            return Ok(context)
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)
    
    def get_context(self, context_id: Optional[str] = None) -> Result['BrowserContext', Exception]:
        """Get a context by ID or the default context"""
        try:
            context_id = context_id or self.default_context_id
            
            if context_id is None:
                return Error(Exception("No contexts available"))
            
            context = self.contexts.get(context_id)
            if context is None:
                return Error(Exception(f"Context with ID '{context_id}' not found"))
            
            return Ok(context)
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return Error(e)
    
    async def close_context(self, context_id: str) -> Result[None, Exception]:
        """Close a specific context and its driver"""
        try:
            context_result = self.get_context(context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            context = context_result.default_value(None)
            if context is None:
                return Error(Exception("Failed to get context"))
            
            try:
                # Await the coroutine returned by context.close()
                close_result = await context.close()
            except Exception as e:
                return Error(e)
            
            # If close_result is a Result object with is_error method
            if hasattr(close_result, 'is_error') and close_result.is_error():
                return close_result
            
            driver = self.drivers.get(context_id)
            if driver:
                try:
                    # Await the driver close coroutine
                    await driver.close()
                except Exception as e:
                    # Log but continue since we've already closed the context
                    logger.warning(f"Error closing driver: {e}")
                    
            self.drivers.pop(context_id, None)
            self.contexts.pop(context_id, None)
            
            if self.default_context_id == context_id:
                contexts = list(self.contexts.keys())
                self.default_context_id = contexts[0] if contexts else None
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing context: {e}")
            return Error(e)

    async def close_all(self) -> Result[None, Exception]:
        """Close all contexts and drivers"""
        try:
            close_results: List[Result[None, Exception]] = []
            for context_id in list(self.contexts.keys()):
                # Fixed: Always await close_result
                close_result = await self.close_context(context_id)
                close_results.append(close_result)
            
            errors = [result.error for result in close_results if result.is_error()]
            if errors:
                return Error(Exception(f"Errors closing contexts: {errors}"))
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing all contexts: {e}")
            return Error(e)
    
    async def execute_action(self, action: Action[T]) -> Result[T, Exception]:
        """
        Execute an action with a new default context
        
        Args:
            action: Action to execute
            
        Returns:
            Result of the action
        """
        # Fixed: Always await context_result
        context_result = await self.create_context(nickname="action-context")
        if context_result.is_error():
            return Error(context_result.error)
        browser_context = context_result.default_value(None)
        if browser_context is None:
            return Error(Exception("Failed to create context"))
        
        try:
            page_result = browser_context.get_page()
            if page_result.is_error():
                return Error(page_result.error)
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))
            
            action_context = ActionContext(
                browser_manager=self,
                context_id=browser_context.id,
                page_id=page.id
            )
            
            # Fixed: Always await action_result
            action_result = await action.execute(action_context)
            
            return action_result
        finally:
            # Fixed: Always await close_context
            await self.close_context(browser_context.id)
    
    @asynccontextmanager
    async def session(
        self, 
        nickname: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> 'AsyncIterator[BrowserContext]':
        """Context manager for a browser session"""
        created = False
        context = None
        
        try:
            if nickname is None or nickname not in self.contexts:
                # Fixed: Always await context_result
                context_result = await self.create_context(
                    nickname=nickname,
                    options=options,
                    create_page=True
                )
                
                if context_result.is_error():
                    raise context_result.error
                
                context = context_result.default_value(None)
                if context is None:
                    raise Exception("Failed to get context")
                created = True
            else:
                context_result = self.get_context(nickname)
                if context_result.is_error():
                    raise context_result.error
                
                context = context_result.default_value(None)
                if context is None:
                    raise Exception("Failed to get context")
            
            yield context
        finally:
            if created and context is not None:
                await self.close_context(context.id)