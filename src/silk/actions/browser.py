"""
Context management actions for Silk pipelines.

These actions allow creating, switching, and modifying browser contexts and pages
within action pipelines, working directly with the Driver, BrowserContext, and Page
protocols from the ActionContext.
"""

import logging
from typing import Any, Dict, Optional, List
from uuid import uuid4

from expression import Error, Ok, Result
from fp_ops import operation

from silk.browsers.models import ActionContext,  BrowserOptions, NavigationOptions, NavigationWaitLiteral, WaitOptions, BrowserContextOptions

logger = logging.getLogger(__name__)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def CreateContext(
    context_options: Optional[BrowserContextOptions] = None,
    create_page: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Creates a new browser context in the current driver.

    Args:
        context_options: Optional browser context options (viewport, permissions, etc.)
        create_page: Whether to create a page automatically in the new context

    Returns:
        Updated ActionContext with the new browser context
    """
    context: ActionContext = kwargs["context"]
    
    if not context.driver:
        return Error(Exception("No driver found in context"))
    
    try:
        if context_options is None:
            context_options = BrowserContextOptions()
        context_result = await context.driver.new_context(context_options)
        if context_result.is_error():
            return Error(context_result.error)
        
        browser_context = context_result.default_value(None)
        if browser_context is None:
            return Error(Exception("No browser context found"))
        
        context_id = browser_context.context_id or f"context_{uuid4().hex[:8]}"
        
        page = None
        page_id = None
        
        if create_page:
            page_result = await browser_context.new_page()
            if page_result.is_error():
                return Error(page_result.error)
            
            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("No page found"))
            
            page_id = page.page_id or f"page_{uuid4().hex[:8]}"
        
        new_context = context.derive(
            context=browser_context,
            page=page,
            context_id=context_id,
            page_id=page_id,
            page_ids={page_id} if page_id else set(),
            metadata={
                **context.metadata,
                "context_options": context_options or {},
            }
        )
        
        logger.info(f"Created new context: {context_id}, page: {page_id}")
        return Ok(new_context)
        
    except Exception as e:
        logger.error(f"Error creating context: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def CreatePage(
    page_nickname: Optional[str] = None,
    switch_to: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Creates a new page in the current browser context.

    Args:
        page_nickname: Optional nickname for the new page, auto-generates one if not provided
        switch_to: Whether to switch to the new page after creation

    Returns:
        Updated ActionContext with the new page if switch_to is True
    """
    context: ActionContext = kwargs["context"]
    
    if not context.context:
        return Error(Exception("No browser context found in context"))
    
    try:
        page_result = await context.context.new_page()
        if page_result.is_error():
            return Error(page_result.error)
        
        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("No page found"))
        
        page_id = page_nickname or page.page_id or f"page_{uuid4().hex[:8]}"
        
        new_page_ids = context.page_ids.copy()
        new_page_ids.add(page_id)
        
        if switch_to:
            new_context = context.derive(
                page=page,
                page_id=page_id,
                page_ids=new_page_ids,
                metadata={
                    **context.metadata,
                    "previous_page_id": context.page_id,
                }
            )
            logger.info(f"Created and switched to new page: {page_id}")
        else:
            new_context = context.derive(page_ids=new_page_ids)
            logger.info(f"Created new page: {page_id} (not switched)")
        
        return Ok(new_context)
        
    except Exception as e:
        logger.error(f"Error creating page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def SwitchToPage(
    page_id: str,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Switches to a different page within the current context.
    
    Note: This requires the driver to support page retrieval by ID,
    which may need to be tracked separately in a real implementation.

    Args:
        page_id: ID of the page to switch to

    Returns:
        Updated ActionContext with the specified page
    """
    context: ActionContext = kwargs["context"]
    
    if not context.context:
        return Error(Exception("No browser context found in context"))
    
    if page_id not in context.page_ids:
        return Error(Exception(f"Page '{page_id}' not found in tracked pages"))
    
    try:
        pages_result = await context.context.pages()
        if pages_result.is_error():
            return Error(pages_result.error)
        
        pages = pages_result.default_value([])
        
        target_page = None
        for page in pages:
            if page.page_id == page_id:
                target_page = page
                break
        
        if not target_page:
            try:
                page_index = int(page_id)
                if 0 <= page_index < len(pages):
                    target_page = pages[page_index]
            except (ValueError, IndexError):
                pass
        
        if not target_page:
            return Error(Exception(f"Could not find page with ID: {page_id}"))
        
        new_context = context.derive(
            page=target_page,
            page_id=page_id,
            metadata={
                **context.metadata,
                "previous_page_id": context.page_id,
            }
        )
        
        logger.info(f"Switched to page: {page_id}")
        return Ok(new_context)
        
    except Exception as e:
        logger.error(f"Error switching page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def CloseCurrentPage(
    switch_to_last: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Closes the current page and optionally switches to another page.

    Args:
        switch_to_last: Whether to switch to the last available page after closing

    Returns:
        Updated ActionContext with a different page or None for page if no pages left
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page:
        return Error(Exception("No page found in context"))
    
    try:
        close_result = await context.page.close()
        if close_result.is_error():
            return Error(close_result.error)
        
        new_page_ids = context.page_ids.copy()
        if context.page_id in new_page_ids:
            new_page_ids.remove(context.page_id)
        
        new_page = None
        new_page_id = None
        
        if switch_to_last and context.context:
            pages_result = await context.context.pages()
            pages = pages_result.default_value([])
            if pages_result.is_ok() and pages:
                new_page = pages[-1]
                new_page_id = new_page.page_id or "last_page"
        
        new_context = context.derive(
            page=new_page,
            page_id=new_page_id,
            page_ids=new_page_ids,
            metadata={
                **context.metadata,
                "closed_page_id": context.page_id,
            }
        )
        
        logger.info(f"Closed page: {context.page_id}, switched to: {new_page_id}")
        return Ok(new_context)
        
    except Exception as e:
        logger.error(f"Error closing page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def CloseContext(
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Closes the current browser context and all its pages.

    Returns:
        Updated ActionContext with no context or pages
    """
    context: ActionContext = kwargs["context"]
    
    if not context.context:
        return Error(Exception("No browser context found in context"))
    
    try:
        close_result = await context.context.close()
        if close_result.is_error():
            return Error(close_result.error)
        
        new_context = context.derive(
            context=None,
            page=None,
            context_id=None,
            page_id=None,
            page_ids=set(),
            metadata={
                **context.metadata,
                "closed_context_id": context.context_id,
            }
        )
        
        logger.info(f"Closed context: {context.context_id}")
        return Ok(new_context)
        
    except Exception as e:
        logger.error(f"Error closing context: {e}")
        return Error(e)

@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def WithNewTab(
    url: Optional[str] = None,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Creates a new tab (page) and optionally navigates to a URL.
    
    This is a convenience action that combines CreatePage and Navigate.

    Args:
        url: Optional URL to navigate to in the new tab

    Returns:
        Updated ActionContext with the new page
    """
    context: ActionContext = kwargs["context"]
    create_result: Result[ActionContext, Exception] = await CreatePage(switch_to=True).execute(**kwargs) # type: ignore[arg-type]
    if create_result.is_error():
        return Error(create_result.error)
    
    new_context = create_result.default_value(None)
    if new_context is None:
        return Error(Exception("No new context found"))
    
    if url and new_context.page:
        nav_result = await new_context.page.goto(url)
        if nav_result.is_error():
            await new_context.page.close()
            return Error(nav_result.error)
        
        new_context = new_context.derive(
            metadata={
                **new_context.metadata,
                "current_url": url,
            }
        )
    
    return Ok(new_context)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetAllPages(
    **kwargs: Any,
) -> Result[List[str], Exception]:
    """
    Gets a list of all page IDs in the current context.

    Returns:
        List of page IDs
    """
    context: ActionContext = kwargs["context"]
    
    if not context.context:
        return Error(Exception("No browser context found in context"))
    
    try:
        pages_result = await context.context.pages()
        if pages_result.is_error():
            return Error(pages_result.error)
        
        pages = pages_result.default_value([])
        
        page_ids = []
        for i, page in enumerate(pages):
            page_id = page.page_id or f"page_{i}"
            page_ids.append(page_id)
        
        return Ok(page_ids)
        
    except Exception as e:
        logger.error(f"Error getting pages: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def FocusPage(
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Focuses/brings to front the current page.
    
    This is useful when working with multiple pages/tabs.

    Returns:
        The same ActionContext (page is focused as a side effect)
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page:
        return Error(Exception("No page found in context"))
    
    try:
        if hasattr(context.page, 'bring_to_front'):
            result = await context.page.bring_to_front()
            if hasattr(result, 'is_error') and result.is_error():
                return Error(result.error)
        
        logger.info(f"Focused page: {context.page_id}")
        return Ok(context)
        
    except Exception as e:
        logger.error(f"Error focusing page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def ReloadPage(
    wait_until: NavigationWaitLiteral = "load",
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Reloads the current page.

    Args:
        wait_until: When to consider the reload complete

    Returns:
        The same ActionContext (page is reloaded as a side effect)
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page:
        return Error(Exception("No page found in context"))
    
    try:
        options = NavigationOptions(wait_until=wait_until)
        reload_result = await context.page.reload(options)
        if reload_result.is_error():
            return Error(reload_result.error)
        
        logger.info(f"Reloaded page: {context.page_id}")
        return Ok(context)
        
    except Exception as e:
        logger.error(f"Error reloading page: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetCurrentUrl(
    **kwargs: Any,
) -> Result[str, Exception]:
    """
    Gets the current URL of the page.

    Returns:
        The current URL as a string
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page:
        return Error(Exception("No page found in context"))
    
    try:
        url_result = await context.page.get_url()
        if url_result.is_error():
            return Error(url_result.error)
        url = url_result.default_value(None)
        if url is None:
            return Error(Exception("No URL found"))
        return Ok(url)
        
    except Exception as e:
        logger.error(f"Error getting URL: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetPageTitle(
    **kwargs: Any,
) -> Result[str, Exception]:
    """
    Gets the title of the current page.

    Returns:
        The page title as a string
    """
    context: ActionContext = kwargs["context"]
    
    if not context.page:
        return Error(Exception("No page found in context"))
    
    try:
        title_result = await context.page.get_title()
        if title_result.is_error():
            return Error(title_result.error)
        title = title_result.default_value(None)
        if title is None:
            return Error(Exception("No title found"))
        return Ok(title)
        
    except Exception as e:
        logger.error(f"Error getting title: {e}")
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def WithMetadata(
    metadata: Dict[str, Any],
    merge: bool = True,
    **kwargs: Any,
) -> Result[ActionContext, Exception]:
    """
    Updates the context with additional metadata.

    Args:
        metadata: Dictionary of metadata to add
        merge: Whether to merge with existing metadata (True) or replace it (False)

    Returns:
        Updated ActionContext with new metadata
    """
    context: ActionContext = kwargs["context"]
    
    if merge:
        final_metadata = {**context.metadata, **metadata}
        new_context = context.derive(metadata=final_metadata)
    else:
        new_context = context.derive()
        new_context.metadata = metadata
    
    return Ok(new_context) 