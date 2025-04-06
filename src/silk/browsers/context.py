"""
Browser context and page management for Silk.

This module provides classes for managing multiple browser contexts and pages,
enabling advanced scraping scenarios with isolated cookie/storage state and
parallel execution.
"""

from typing import Dict, List, Optional, Any, Union, cast
from pathlib import Path
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from expression.core import Result, Ok, Error

from silk.browsers.driver import BrowserDriver, BrowserOptions
from silk.models.browser import NavigationOptions, WaitOptions, ActionContext

logger = logging.getLogger(__name__)


# todo clean this up
# we will replace the use of driver in action execution with context
# we will use drivers as a context manager

# ex async with BrowserDriver() as driver: 
# actions will pass around an ActionContext which contains a browser context id and page id 
# the context will be created by the BrowserManager ? not sure yet

# our actions will need helpers to be able to use the context and pages easily 
# ex we should be able to do context.go_to(url) and have that create a page if it doesn't exist and navigate to the url? 
# we should read they playwright api and use that as inspiration for our framework

# ideally experience

# Navigate >> WaitForSelector >> Click >> Fill >> Keyboard >> Screenshot
# all the actions are chainable and can be piped together and will use the same context passed down via .execute()

# if we do 
# Navigate | Navigate | Navigate 
# The navigates will use the same context, while independent of each other they happen sequentially as | is a fall back operator

# if we do
# Navigate & Navigate & Navigate
# The navigates will use different contexts, as these are parallel tasks

# if we do
# (Navigate1 >> Click) & (Navigate2 >> Fill)
# the click will use navigate1's context as its a sequential task, fill will use navigate2's context as its a sequential task, but the navigates use different contexts as they are parallel tasks with no parent context


# if we do
# (Navigate1 >> Click) >> (Navigate2 >> Fill)
# the click will use navigate1's context and the fill will use navigate2's context as they are sequential


# essentially we will always use the parent context for sequential tasks
# and we will use a new context for each parallel task with no parent context
# we will always use the default/active page for the context


# we will need util actions for use to declare what context or page we want to use

















class BrowserPage:
    """
    Represents a single page (tab) in a browser context
    """
    
    def __init__(
        self, 
        page_id: str,
        context_id: str,
        driver: BrowserDriver,
        driver_page: Any
    ):
        self.id = page_id
        self.context_id = context_id
        self.driver = driver
        self.driver_page = driver_page
    
    async def goto(
        self, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate to a URL in this page"""
        try:
            return await self.driver.page_goto(
                self.context_id, 
                self.id, 
                url, 
                options
            )
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return Error(e)
    
    async def close(self) -> Result[None, Exception]:
        """Close this page"""
        try:
            return await self.driver.close_page(self.context_id, self.id)
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)

    # Delegate other methods to the driver with context_id and page_id
    async def query_selector(self, selector: str) -> Result[Any, Exception]:
        return await self.driver.page_query_selector(self.context_id, self.id, selector)
    
    async def query_selector_all(self, selector: str) -> Result[List[Any], Exception]:
        return await self.driver.page_query_selector_all(self.context_id, self.id, selector)
    
    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        return await self.driver.page_execute_script(self.context_id, self.id, script, *args)
    
    async def wait_for_selector(
        self, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Any, Exception]:
        return await self.driver.page_wait_for_selector(self.context_id, self.id, selector, options)
    
    async def wait_for_navigation(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.page_wait_for_navigation(self.context_id, self.id, options)
    
    async def take_screenshot(self, path: Path) -> Result[None, Exception]:
        return await self.driver.page_take_screenshot(self.context_id, self.id, path)
    
    async def get_page_source(self) -> Result[str, Exception]:
        return await self.driver.page_get_source(self.context_id, self.id)


class BrowserContext:
    """
    Represents a browser context with its own session state
    (cookies, localStorage, etc.)
    """
    
    def __init__(
        self, 
        context_id: str,
        driver: BrowserDriver,
        options: Optional[Dict[str, Any]] = None
    ):
        self.id = context_id
        self.driver = driver
        self.options = options or {}
        self.pages: Dict[str, BrowserPage] = {}
        self.default_page_id: Optional[str] = None
    
    async def create_page(self, page_id: Optional[str] = None) -> Result[BrowserPage, Exception]:
        """Create a new page in this context"""
        try:
            # Generate page ID if not provided
            if page_id is None:
                page_id = str(uuid4())
            
            # Check if page ID already exists
            if page_id in self.pages:
                return Error(Exception(f"Page with ID '{page_id}' already exists"))
            
            # Create a new page using the driver
            page_result = await self.driver.create_page(self.id)
            if page_result.is_error():
                return page_result
            
            page = BrowserPage(
                page_id=page_id,
                context_id=self.id,
                driver=self.driver,
                driver_page=page_result.value
            )
            
            # Store the new page
            self.pages[page_id] = page
            
            # Set as default page if none exists yet
            if self.default_page_id is None:
                self.default_page_id = page_id
            
            return Ok(page)
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return Error(e)
    
    def get_page(self, page_id: Optional[str] = None) -> Result[BrowserPage, Exception]:
        """Get a page by ID or the default page"""
        try:
            # Use default page if ID not specified
            page_id = page_id or self.default_page_id
            
            # Check if page exists
            if page_id is None:
                return Error(Exception("No pages available in this context"))
            
            page = self.pages.get(page_id)
            if page is None:
                return Error(Exception(f"Page with ID '{page_id}' not found"))
            
            return Ok(page)
        except Exception as e:
            logger.error(f"Error getting page: {e}")
            return Error(e)
    
    async def close(self) -> Result[None, Exception]:
        """Close the context and all associated pages"""
        try:
            # Close all pages
            close_results = []
            for page in list(self.pages.values()):
                close_results.append(await page.close())
            
            # Clear the pages dictionary
            self.pages.clear()
            self.default_page_id = None
            
            # Close the context in the driver
            return await self.driver.close_context(self.id)
        except Exception as e:
            logger.error(f"Error closing context: {e}")
            return Error(e)


class BrowserManager:
    """
    Manages multiple browser contexts and their pages
    """
    
    def __init__(self, driver_factory, default_options: BrowserOptions):
        self.driver_factory = driver_factory
        self.default_options = default_options
        self.drivers: Dict[str, BrowserDriver] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.default_context_id: Optional[str] = None
    
    async def create_context(
        self, 
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        create_page: bool = True
    ) -> Result[BrowserContext, Exception]:
        """Create a new browser context"""
        try:
            # Generate context ID if not provided
            if context_id is None:
                context_id = str(uuid4())
            
            # Check if context ID already exists
            if context_id in self.contexts:
                return Error(Exception(f"ActionContext with ID '{context_id}' already exists"))
            
            # Create a driver for this context if we don't have one already
            if context_id not in self.drivers:
                driver = self.driver_factory(self.default_options)
                
                # Launch the driver
                launch_result = await driver.launch()
                if launch_result.is_error():
                    return launch_result
                
                # Store the driver
                self.drivers[context_id] = driver
            else:
                driver = self.drivers[context_id]
            
            # Create the context
            context_result = await driver.create_context(options)
            if context_result.is_error():
                return context_result
            
            # Create a BrowserContext object
            context = BrowserContext(
                context_id=context_id,
                driver=driver,
                options=options
            )
            
            # Store the context
            self.contexts[context_id] = context
            
            # Set as default context if none exists yet
            if self.default_context_id is None:
                self.default_context_id = context_id
            
            # Create a default page if requested
            if create_page:
                page_result = await context.create_page()
                if page_result.is_error():
                    return page_result
            
            return Ok(context)
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)
    
    def get_context(self, context_id: Optional[str] = None) -> Result[BrowserContext, Exception]:
        """Get a context by ID or the default context"""
        try:
            # Use default context if ID not specified
            context_id = context_id or self.default_context_id
            
            # Check if context exists
            if context_id is None:
                return Error(Exception("No contexts available"))
            
            context = self.contexts.get(context_id)
            if context is None:
                return Error(Exception(f"ActionContext with ID '{context_id}' not found"))
            
            return Ok(context)
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return Error(e)
    
    async def close_context(self, context_id: str) -> Result[None, Exception]:
        """Close a specific context and its driver"""
        try:
            # Get the context
            context_result = self.get_context(context_id)
            if context_result.is_error():
                return context_result
            
            context = context_result.value
            
            # Close the context
            close_result = await context.close()
            if close_result.is_error():
                return close_result
            
            # Get the driver
            driver = self.drivers.get(context_id)
            if driver:
                # Close the driver
                await driver.close()
                
                # Remove the driver
                self.drivers.pop(context_id, None)
            
            # Remove the context
            self.contexts.pop(context_id, None)
            
            # Update default context if needed
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
            # Close all contexts
            close_results = []
            for context_id in list(self.contexts.keys()):
                close_results.append(await self.close_context(context_id))
            
            # Check for errors
            errors = [result.error for result in close_results if result.is_error()]
            if errors:
                return Error(Exception(f"Errors closing contexts: {errors}"))
            
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing all contexts: {e}")
            return Error(e)
    
    @asynccontextmanager
    async def session(
        self, 
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        """ActionContext manager for a browser session"""
        created = False
        context = None
        
        try:
            if context_id is None or context_id not in self.contexts:
                context_result = await self.create_context(
                    context_id=context_id,
                    options=options,
                    create_page=True
                )
                
                if context_result.is_error():
                    raise context_result.error
                
                context = context_result.value
                created = True
            else:
                # Get existing context
                context_result = self.get_context(context_id)
                if context_result.is_error():
                    raise context_result.error
                
                context = context_result.value
            
            yield context
        finally:
            if created and context is not None:
                await self.close_context(context.id)