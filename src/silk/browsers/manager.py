import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, TypeVar, Union

from expression import Error, Ok, Result

from silk.browsers.context import BrowserContext
from silk.browsers.driver import BrowserDriver
from silk.browsers.driver_factory import ValidDriverTypes, create_driver
from silk.browsers.types import BrowserOptions

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BrowserManager:
    """
    Manages multiple browser contexts and their pages for parallel and sequential execution.
    Acts as the main entry point for executing actions.
    """

    def __init__(
        self,
        driver_type: Optional[ValidDriverTypes] = "playwright",
        default_options: Optional[BrowserOptions] = None,
        remote_url: Optional[str] = None,
    ):
        """
        Initialize the browser manager

        Args:
            driver_type: The type of driver to use. Valid values are
            'playwright', 'cdp'. Defaults to 'playwright'
            default_options: Default browser options
            remote_url: URL for connecting to a remote CDP browser. Setting this will 
                        automatically use the 'cdp' driver type.
        """
        self.default_options = default_options or BrowserOptions()
        
        # If remote_url is provided, set it in options and use cdp driver
        if remote_url:
            self.default_options.remote_url = remote_url
            self.driver_type: ValidDriverTypes = "cdp"
        else:
            self.driver_type = driver_type or "playwright"
            
        self.drivers: Dict[str, BrowserDriver] = {}
        self.contexts: Dict[str, "BrowserContext"] = {}
        self.default_context_id: Optional[str] = None

    async def __aenter__(self) -> "BrowserManager":
        """Allow usage as async context manager"""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Clean up when exiting the context manager"""
        await self.close_all()

    async def create_context(
        self,
        nickname: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        create_page: bool = True,
    ) -> Result["BrowserContext", Exception]:
        """Create a new browser context"""
        try:
            context_id = nickname or f"context-{len(self.contexts) + 1}"

            if context_id in self.contexts:
                return Error(
                    Exception(f"Context with ID '{context_id}' already exists")
                )

            if context_id not in self.drivers:
                driver_type = self.driver_type or "playwright"
                driver = create_driver(driver_type, self.default_options)

                launch_result = await driver.launch()

                if launch_result.is_error():
                    return Error(launch_result.error)

                self.drivers[context_id] = driver
            else:
                driver = self.drivers[context_id]

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
                context_ref=context_ref,
                nickname=nickname,  # Pass the nickname parameter
            )

            self.contexts[context_id] = context

            if self.default_context_id is None:
                self.default_context_id = context_id

            if create_page:
                page_result = await context.create_page()

                if page_result.is_error():
                    return Error(page_result.error)

            return Ok(context)
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)
    # In BrowserManager class (paste-3.txt)
    def get_context(
        self, context_id_or_nickname: Optional[str] = None
    ) -> Result["BrowserContext", Exception]:
        """Get a context by ID or the default context"""
        try:
            context_id = context_id_or_nickname or self.default_context_id

            if context_id is None:
                return Error(Exception("No contexts available"))

            # First, try direct lookup by ID in the contexts dictionary
            if context_id in self.contexts:
                return Ok(self.contexts[context_id])
            
            # If not found by ID, try to find by nickname
            found_context = None
            for ctx in self.contexts.values():
                if ctx.nickname == context_id:
                    found_context = ctx
                    break

            if found_context is None:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            return Ok(found_context)
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
                close_result = await context.close()
            except Exception as e:
                return Error(e)

            if hasattr(close_result, "is_error") and close_result.is_error():
                return close_result

            driver = self.drivers.get(context_id)
            if driver:
                try:
                    await driver.close()
                except Exception as e:
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
                close_result = await self.close_context(context_id)
                close_results.append(close_result)

            errors = [result.error for result in close_results if result.is_error()]
            if errors:
                return Error(Exception(f"Errors closing contexts: {errors}"))
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing all contexts: {e}")
            return Error(e)

    @asynccontextmanager
    async def session(
        self, nickname: Optional[str] = None, options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[BrowserContext]:
        """Context manager for a browser session"""
        created = False
        context = None

        try:
            if nickname is None or nickname not in self.contexts:
                context_result = await self.create_context(
                    nickname=nickname, options=options, create_page=True
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
