import logging
from typing import Optional, Dict, Any, Type
from silk.browsers.models import ActionContext, BrowserContext, BrowserContextOptions, BrowserOptions, Driver, Page
from types import TracebackType

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    A browser session manager that handles the lifecycle of browser automation.

    This class manages the creation and cleanup of browser contexts and pages,
    providing a convenient interface for browser automation tasks. It supports
    both async context manager usage and manual lifecycle management.

    Args:
        options (BrowserOptions, optional): Browser launch options
        driver_class (Type[Driver]): The browser driver class to use (e.g., PlaywrightDriver)
        create_context (bool, optional): Whether to create a browser context on start. Defaults to True
        create_page (bool, optional): Whether to create a page on start. Defaults to True
        context_options (Dict[str, Any], optional): Options for browser context creation
        page_nickname (str, optional): Optional nickname for the created page

    Examples:
        Using as an async context manager (recommended):
        ```python
        session = BrowserSession(options, driver_class=PlaywrightDriver)
        
        async with session as ctx:
            # ctx is an ActionContext that can be used for browser operations
            await Fill("#search", "query").execute(ctx)
            await Click("#submit").execute(ctx)
        ```

        Manual lifecycle management:
        ```python
        session = BrowserSession(options, driver_class=PlaywrightDriver)
        
        # Start the session and get the action context
        await session.start()
        ctx = session.context
        
        # Use the context for operations
        await ctx.fill("#search", "query")
        await ctx.click("#submit")
        
        # Clean up when done
        await session.close()
        ```

    Note:
        The async context manager approach is recommended as it ensures proper
        cleanup of browser resources even if an error occurs.
    """
    
    def __init__(
        self,
        options: Optional[BrowserOptions] = None,
        driver_class: Optional[Type[Driver]] = None,
        create_context: bool = True,
        create_page: bool = True,
        context_options: Optional[BrowserContextOptions] = None,
        page_nickname: Optional[str] = None,
    ):
        if driver_class is None:
            raise ValueError("driver_class must be provided")
        
        self.options = options or BrowserOptions()
        self.driver_class = driver_class
        self.create_context = create_context
        self.create_page = create_page
        self.context_options = context_options
        self.page_nickname = page_nickname
        
        self.driver: Optional[Driver] = None
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.context: Optional[ActionContext] = None
        self._started = False
    
    async def start(self) -> ActionContext:
        """Start the browser session and return the action context."""
        if self._started:
            raise RuntimeError("Session already started")
        
        try:
            self.driver = self.driver_class()
            
            launch_result = await self.driver.launch(self.options)
            if launch_result.is_error():
                raise launch_result.error
            
            context_id = None
            page_id = None
            
            if self.create_context:
                context_result = await self.driver.new_context(self.context_options)
                if context_result.is_error():
                    raise context_result.error
                
                self.browser_context = context_result.default_value(None)
                if self.browser_context is None:
                    raise Exception("Context creation failed")
                
                context_id = self.browser_context.context_id or "default"
                
                if self.create_page:
                    page_result = await self.browser_context.new_page()
                    if page_result.is_error():
                        raise page_result.error
                    
                    self.page = page_result.default_value(None)
                    if self.page is None:
                        raise Exception("Page creation failed")
                    
                    page_id = self.page_nickname or self.page.page_id or "default"
            
            self.context = ActionContext(
                driver=self.driver,
                context=self.browser_context,
                page=self.page,
                driver_type=self.driver_class.__name__.lower().replace('driver', ''),
                context_id=context_id,
                page_id=page_id,
                page_ids={page_id} if page_id else set(),
                metadata={
                    "browser_options": self.options.model_dump(),
                    "context_options": self.context_options or {},
                }
            )
            
            self._started = True
            return self.context
            
        except Exception as e:
            await self._cleanup()
            raise
    
    async def close(self) -> None:
        """Close the browser session."""
        if not self._started:
            return
        
        await self._cleanup()
        self._started = False
    
    async def _cleanup(self) -> None:
        """Internal cleanup method."""
        if self.page is not None:
            try:
                await self.page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")
        
        if self.browser_context is not None:
            try:
                await self.browser_context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")
        
        if self.driver is not None:
            try:
                await self.driver.close()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
        
        self.page = None
        self.browser_context = None
        self.driver = None
        self.context = None
    
    async def __aenter__(self) -> ActionContext:
        return await self.start()
    
    async def __aexit__(self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb: Optional[TracebackType]) -> None:
        await self.close()
