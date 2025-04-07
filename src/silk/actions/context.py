import logging
from typing import Any, Dict, Optional, TypeVar

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.models.browser import ActionContext

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CreateContext(Action[ActionContext]):
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
        create_page: bool = True,
    ):
        self.nickname = nickname
        self.options = options
        self.create_page = create_page

    async def execute(self, context: ActionContext) -> Result[ActionContext, Exception]:
        """Create a new browser context and return the updated ActionContext"""
        if not context.browser_manager:
            return Error(Exception("Browser manager is required"))

        try:
            context_result = await context.browser_manager.create_context(
                nickname=self.nickname,
                options=self.options,
                create_page=self.create_page,
            )
            if context_result.is_error():
                return Error(context_result.error)

            context_id = context_result.default_value(None)
            if context_id is None:
                return Error(Exception("Failed to create context"))

            new_context = context.derive(context_id=context_id)
            return Ok(new_context)
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
            context_result = context.browser_manager.get_context(
                self.context_id_or_nickname
            )
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            context.context_id = browser_context.id

            if browser_context.default_page_id:
                context.page_id = browser_context.default_page_id
            else:
                context.page_id = None

            return Ok(None)
        except Exception as e:
            logger.error(f"Error switching context: {e}")
            return Error(e)


class CreatePage(Action[ActionContext]):
    """
    Create a new page in the current context

    Args:
        nickname: Optional nickname for the page
    """

    def __init__(self, nickname: Optional[str] = None):
        self.nickname = nickname

    async def execute(self, context: ActionContext) -> Result[ActionContext, Exception]:
        """Create a new page and return the updated context"""
        if not context.browser_manager or not context.context_id:
            return Error(Exception("Browser manager and context ID are required"))

        try:
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            page_result = await browser_context.create_page(nickname=self.nickname)
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to create page"))

            context.page_id = page.id

            return Ok(context)
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
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            page_result = browser_context.get_page(self.page_id_or_nickname)
            if page_result.is_error():
                # If page isn't found in current context, we just return the error
                # since we don't have a way to look up pages by nickname across contexts
                return Error(page_result.error)

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
            target_context_id = self.context_id_or_nickname or context.context_id
            if not target_context_id:
                return Error(Exception("No context specified to close"))

            close_result = await context.browser_manager.close_context(
                target_context_id
            )
            if close_result.is_error():
                return Error(close_result.error)

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
            context_result = context.browser_manager.get_context(context.context_id)
            if context_result.is_error():
                return Error(context_result.error)

            browser_context = context_result.default_value(None)
            if browser_context is None:
                return Error(Exception("Failed to get browser context"))

            target_page_id = self.page_id_or_nickname or context.page_id
            if not target_page_id:
                return Error(Exception("No page specified to close"))

            page_result = browser_context.get_page(target_page_id)
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page"))

            close_result = await page.close()
            if close_result.is_error():
                return Error(close_result.error)

            if context.page_id == page.id:
                context.page_id = browser_context.default_page_id

            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)
