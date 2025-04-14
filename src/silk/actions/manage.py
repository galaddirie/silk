"""
Context management actions for Silk pipelines.

These actions allow creating, switching, and modifying browser contexts and pages
within action pipelines, making it easier to initialize pipelines from a BrowserManager
and manage browser contexts throughout a workflow.
"""

import logging
from typing import Any, Dict, Optional, Union

from expression import Error, Ok, Result
from fp_ops import operation

from silk.actions.context import ActionContext
from silk.browsers.manager import BrowserManager

from silk.operation import Operation

logger = logging.getLogger(__name__)


# cant be oepration, must be a function
async def InitializeContext(
    manager: BrowserManager,
    context_id: Optional[str] = None,
    page_nickname: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    create_page: bool = True,
) -> ActionContext: 
    """
    Creates a context from a BrowserManager to initialize a pipeline.
    This is the starting point for most pipelines, converting a BrowserManager
    into an ActionContext that can be used by other actions.

    Args:
        manager: The BrowserManager to create a context from
        context_id: Optional ID for the context, generates one if not provided
        page_nickname: Optional nickname for the page, uses default if not provided
        options: Optional browser context options
        create_page: Whether to create a page automatically

    Returns:
        ActionContext that can be used with other actions
    """
    try:
        # Check if we're using a specified existing context
        if context_id is not None and context_id in manager.contexts:
            context_result = manager.get_context(context_id)
            if context_result.is_error():
                raise context_result.error
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                raise Exception("Context not found")

            if browser_context.id is None:
                raise Exception("Context ID not found")
            
            # Get or create the specified page
            if page_nickname is not None:
                if page_nickname in browser_context.pages:
                    # Use existing page
                    actual_page_id = page_nickname
                else:
                    # Create new page with specified ID
                    page_result = await browser_context.create_page(nickname=page_nickname)
                    if page_result.is_error():
                        raise page_result.error
                    actual_page_id = page_nickname
            else:
                # Use default page or create one
                if browser_context.pages:
                    actual_page_id = list(browser_context.pages.keys())[0]
                elif create_page:
                    page_result = await browser_context.create_page(nickname=page_nickname)
                    if page_result.is_error():
                        raise page_result.error
                    actual_page_id = list(browser_context.pages.keys())[0]
                else:
                    actual_page_id = None
        else:
            # Create a new context
            context_result = await manager.create_context(
                nickname=context_id, options=options, create_page=create_page
            )
            if context_result.is_error():
                raise context_result.error
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                raise Exception("Context not found")
            
            # Get the page ID if a page was created
            if create_page and browser_context.pages:
                actual_page_id = list(browser_context.pages.keys())[0]
            else:
                actual_page_id = None
        
        # Create the ActionContext
        action_context = ActionContext(
            browser_manager=manager,
            context_id=browser_context.id,
            page_id=actual_page_id,
        )
        
        return action_context
    except Exception as e:
        logger.error(f"Error creating context: {e}")
        raise e

@operation
async def WithContext(
    manager: BrowserManager,
    context_id: Optional[str] = None,
    page_nickname: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    create_page: bool = True,
) -> Result[ActionContext, Exception]:
    """
    Creates a context from a BrowserManager to initialize a pipeline.
    This is the starting point for most pipelines, converting a BrowserManager
    into an ActionContext that can be used by other actions.

    Args:
        manager: The BrowserManager to create a context from
        context_id: Optional ID for the context, generates one if not provided
        page_nickname: Optional nickname for the page, uses default if not provided
        options: Optional browser context options
        create_page: Whether to create a page automatically

    Returns:
        ActionContext that can be used with other actions
    """
    try:
        # Check if we're using a specified existing context
        if context_id is not None and context_id in manager.contexts:
            context_result = manager.get_context(context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                return Error(Exception("Context not found"))

            if browser_context.id is None:
                return Error(Exception("Context ID not found"))
            
            # Get or create the specified page
            if page_nickname is not None:
                if page_nickname in browser_context.pages:
                    # Use existing page
                    actual_page_id = page_nickname
                else:
                    # Create new page with specified ID
                    page_result = await browser_context.create_page(nickname=page_nickname)
                    if page_result.is_error():
                        return Error(page_result.error)
                    actual_page_id = page_nickname
            else:
                # Use default page or create one
                if browser_context.pages:
                    actual_page_id = list(browser_context.pages.keys())[0]
                elif create_page:
                    page_result = await browser_context.create_page(nickname=page_nickname)
                    if page_result.is_error():
                        return Error(page_result.error)
                    actual_page_id = list(browser_context.pages.keys())[0]
                else:
                    actual_page_id = None
        else:
            # Create a new context
            context_result = await manager.create_context(
                nickname=context_id, options=options, create_page=create_page
            )
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                return Error(Exception("Context not found"))
            
            # Get the page ID if a page was created
            if create_page and browser_context.pages:
                actual_page_id = list(browser_context.pages.keys())[0]
            else:
                actual_page_id = None
        
        # Create the ActionContext
        action_context = ActionContext(
            browser_manager=manager,
            context_id=browser_context.id,
            page_id=actual_page_id,
        )
        
        return Ok(action_context)
    except Exception as e:
        logger.error(f"Error creating context: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def SwitchContext(
    context_id: str,
    options: Optional[Dict[str, Any]] = None,
    create_page: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Switches to a different browser context or creates a new one.

    Args:
        context_id: ID of the context to switch to or create
        options: Optional browser context options when creating
        create_page: Whether to create a page automatically when creating context

    Returns:
        Updated ActionContext with the new context
    """
    context: ActionContext = kwargs["context"]
    
    if not context.browser_manager:
        return Error(Exception("No browser manager found in context"))
    
    try:
        manager = context.browser_manager
        
        # Check if the context exists
        if context_id in manager.contexts:
            # Get existing context
            context_result = manager.get_context(context_id)
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                return Error(Exception("Context not found"))
            
            # Get default page ID if any pages exist
            page_id = None
            if browser_context.pages:
                page_id = list(browser_context.pages.keys())[0]
            elif create_page:
                # Create a new page if requested
                page_result = await browser_context.create_page()
                if page_result.is_error():
                    return Error(page_result.error)
                page_id = list(browser_context.pages.keys())[0]
        else:
            # Create a new context
            context_result = await manager.create_context(
                nickname=context_id, options=options, create_page=create_page
            )
            if context_result.is_error():
                return Error(context_result.error)
            
            browser_context = context_result.default_value(None)

            if browser_context is None:
                return Error(Exception("Context not found"))
            
            # Get page ID if created
            page_id = None
            if create_page and browser_context.pages:
                page_id = list(browser_context.pages.keys())[0]
        
        # Create new action context with updated values
        new_context = context.derive(
            context_id=browser_context.id,
            page_id=page_id,
        )
        
        return Ok(new_context)
    except Exception as e:
        logger.error(f"Error switching context: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def SwitchPage(
    page_nickname_or_id: Optional[str] = None,
    create_if_missing: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Switches to a different page within the current context or creates a new one.

    Args:
        page_nickname_or_id: Nickname or ID of the page to switch to or create, uses auto-generated nickname if None
        create_if_missing: Whether to create the page if it doesn't exist

    Returns:
        Updated ActionContext with the new page
    """
    context: ActionContext = kwargs["context"]
    
    if not context.browser_manager or not context.context_id:
        return Error(Exception("Browser manager or context ID missing in context"))
    
    try:
        manager = context.browser_manager
        
        # Get the current context
        context_result = manager.get_context(context.context_id)
        if context_result.is_error():
            return Error(context_result.error)
        
        browser_context = context_result.default_value(None)
        
        if browser_context is None:
            return Error(Exception("Context not found"))
        
        # Switch to existing page or create new one
        if page_nickname_or_id is not None:
            # Check if the page exists
            if page_nickname_or_id in browser_context.pages:
                actual_page_id = page_nickname_or_id
            elif create_if_missing:
                # Create a new page with the specified ID
                page_result = await browser_context.create_page(nickname=page_nickname_or_id)
                if page_result.is_error():
                    return Error(page_result.error)
                actual_page_id = page_nickname_or_id
            else:
                return Error(Exception(f"Page '{page_nickname_or_id}' not found and create_if_missing is False"))
        else:
            # Create a new page with auto-generated ID
            page_result = await browser_context.create_page()
            if page_result.is_error():
                return Error(page_result.error)
            actual_page_id = list(browser_context.pages.keys())[-1]
        
        # Create new action context with updated page ID
        new_context = context.derive(page_id=actual_page_id)
        
        return Ok(new_context)
    except Exception as e:
        logger.error(f"Error switching page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def CreatePage(
    page_nickname_or_id: Optional[str] = None,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Creates a new page in the current context and switches to it.

    Args:
        page_nickname_or_id: Optional nickname or ID for the new page, auto-generates one if not provided

    Returns:
        Updated ActionContext with the new page
    """
    context: ActionContext = kwargs["context"]
    
    if not context.browser_manager or not context.context_id:
        return Error(Exception("Browser manager or context ID missing in context"))
    
    try:
        manager = context.browser_manager
        
        # Get the current context
        context_result = manager.get_context(context.context_id)
        if context_result.is_error():
            return Error(context_result.error)
        
        browser_context = context_result.default_value(None)

        if browser_context is None:
            return Error(Exception("Context not found"))
        
        # Create a new page
        page_result = await browser_context.create_page(nickname=page_nickname_or_id)
        if page_result.is_error():
            return Error(page_result.error)
        
        # Get the ID of the created page
        if page_nickname_or_id is not None:
            actual_page_id = page_nickname_or_id
        else:
            actual_page_id = list(browser_context.pages.keys())[-1]
        
        # Create new action context with updated page ID
        new_context = context.derive(page_id=actual_page_id)
        
        return Ok(new_context)
    except Exception as e:
        logger.error(f"Error creating page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def CloseContext(
    **kwargs: Any,
) -> Result[None, Exception]:
    """
    Closes the current browser context.

    Returns:
        Result with None on success or error on failure
    """
    context: ActionContext = kwargs["context"]
    
    if not context.browser_manager or not context.context_id:
        return Error(Exception("Browser manager or context ID missing in context"))
    
    try:
        manager = context.browser_manager
        
        # Close the context
        close_result = await manager.close_context(context.context_id)
        if close_result.is_error():
            return Error(close_result.error)
        
        return Ok(None)
    except Exception as e:
        logger.error(f"Error closing context: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def ClosePage(
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Closes the current page and switches to another page in the context if available.

    Returns:
        Updated ActionContext with a different page or None for page ID if no pages left
    """
    context: ActionContext = kwargs["context"]
    
    if (
        not context.browser_manager or 
        not context.context_id or 
        not context.page_id
    ):
        return Error(Exception("Browser manager, context ID, or page ID missing in context"))
    
    try:
        manager = context.browser_manager
        
        # Get the current context
        context_result = manager.get_context(context.context_id)
        if context_result.is_error():
            return Error(context_result.error)
        
        browser_context = context_result.default_value(None)

        if browser_context is None:
            return Error(Exception("Context not found"))
        
        # Close the current page
        close_result = await browser_context.close_page(context.page_id)
        if close_result.is_error():
            return Error(close_result.error)
        
        # Find another page to switch to if available
        new_page_id = None
        if browser_context.pages:
            new_page_id = list(browser_context.pages.keys())[0]
        
        # Create new action context with updated page ID
        new_context = context.derive(page_id=new_page_id)
        
        return Ok(new_context)
    except Exception as e:
        logger.error(f"Error closing page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetCurrentContext(
    **kwargs: Any,
) -> Result[str, Exception]:
    """
    Gets the ID of the current browser context.

    Returns:
        Result with the context ID
    """
    context: ActionContext = kwargs["context"]
    
    if not context.context_id:
        return Error(Exception("No context ID in current context"))
    
    return Ok(context.context_id)


@operation(context=True, context_type=ActionContext)
async def GetCurrentPage(
    **kwargs: Any,
) -> Result[str, Exception]:
    """
    Gets the ID of the current page.

    Returns:
        Result with the page ID
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page_id:
        return Error(Exception("No page ID in current context"))
    
    return Ok(context.page_id)


@operation(context=True, context_type=ActionContext)
async def WithOptions(
    options: Dict[str, Any],
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Updates the context with additional options or metadata.

    Args:
        options: Dictionary of options to add to context metadata

    Returns:
        Updated ActionContext with new options
    """
    context: ActionContext = kwargs["context"]
    
    # Create new action context with updated metadata
    new_context = context.derive(metadata=options)
    
    return Ok(new_context)