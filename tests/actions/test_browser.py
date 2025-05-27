"""
Tests for Silk context management actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from expression import Error, Ok, Result

from silk.actions.browser import (
    CreateContext, CreatePage, SwitchToPage, CloseCurrentPage,
    CloseContext, WithNewTab, GetAllPages, FocusPage, ReloadPage,
    GetCurrentUrl, GetPageTitle, WithMetadata
)
from silk.browsers.models import ActionContext, BrowserContext, Page, Driver, NavigationOptions


def create_mock_page(page_id="mock-page-id"):
    """Create a mock page that implements the Page protocol."""
    mock = MagicMock()
    mock.page_id = page_id
    mock.page_ref = f"{page_id}-ref"
    mock.get_page_id = MagicMock(return_value=page_id)
    mock.close = AsyncMock(return_value=Ok(None))
    return mock


def create_mock_context(context_id="mock-context-id", pages=None):
    """Create a mock context that implements the BrowserContext protocol."""
    mock = MagicMock()
    mock.context_id = context_id
    mock.page_id = "default-page-id"
    mock.context_ref = f"{context_id}-ref"
    mock.get_page_id = MagicMock(return_value="default-page-id")
    
    if pages is None:
        pages = {"default-page-id": create_mock_page("default-page-id")}
    mock._pages = pages
    
    async def mock_new_page():
        page_id = f"page-{len(mock._pages) + 1}"
        page = create_mock_page(page_id)
        mock._pages[page_id] = page
        return Ok(page)
    
    async def mock_create_page(nickname=None):
        page_id = nickname or f"page-{len(mock._pages) + 1}"
        if page_id in mock._pages:
            return Error(Exception(f"Page '{page_id}' already exists"))
        page = create_mock_page(page_id)
        mock._pages[page_id] = page
        return Ok(page)
    
    async def mock_get_page(page_id=None):
        if page_id is None:
            page_id = "default-page-id"
        if page_id in mock._pages:
            return Ok(mock._pages[page_id])
        return Error(Exception(f"Page '{page_id}' not found"))
    
    async def mock_close_page(page_id=None):
        if page_id is None:
            page_id = "default-page-id"
        if page_id in mock._pages:
            del mock._pages[page_id]
            return Ok(None)
        return Error(Exception(f"Page '{page_id}' not found"))
    
    async def mock_pages():
        return Ok(list(mock._pages.values()))
    
    mock.new_page = mock_new_page
    mock.create_page = mock_create_page
    mock.get_page = mock_get_page
    mock.close_page = mock_close_page
    mock.pages = mock_pages
    mock.close = AsyncMock(return_value=Ok(None))
    
    return mock


@pytest.mark.asyncio
async def test_create_context_with_page(action_context, mock_driver, mock_browser_context, mock_page):
    """Test CreateContext creates a new context with a page."""
    mock_driver.new_context = AsyncMock(return_value=Ok(mock_browser_context))
    mock_browser_context.new_page = AsyncMock(return_value=Ok(mock_page))
    
    action_context.driver = mock_driver
    
    create_context = CreateContext(create_page=True)
    result = await create_context(context=action_context)
    
    assert result.is_ok(), f"CreateContext failed: {result.error if result.is_error() else ''}"
    new_context = result.default_value(None)
    
    assert isinstance(new_context, ActionContext)
    assert new_context.driver == mock_driver
    assert new_context.context == mock_browser_context
    assert new_context.page == mock_page
    assert new_context.page_id is not None
    
    mock_driver.new_context.assert_called_once()
    mock_browser_context.new_page.assert_called_once()


@pytest.mark.asyncio
async def test_create_context_without_page(action_context, mock_driver, mock_browser_context):
    """Test CreateContext without creating a page."""
    mock_driver.new_context = AsyncMock(return_value=Ok(mock_browser_context))
    
    action_context.driver = mock_driver
    
    create_context = CreateContext(create_page=False)
    result = await create_context(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.context == mock_browser_context
    assert new_context.page is None
    assert new_context.page_id is None
    mock_browser_context.new_page.assert_not_called()


@pytest.mark.asyncio
async def test_create_context_with_options(action_context, mock_driver, mock_browser_context):
    """Test CreateContext with custom context options."""
    context_options = {"viewport": {"width": 1920, "height": 1080}}
    mock_driver.new_context = AsyncMock(return_value=Ok(mock_browser_context))
    
    action_context.driver = mock_driver
    
    create_context = CreateContext(context_options=context_options, create_page=False)
    result = await create_context(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    mock_driver.new_context.assert_called_once_with(context_options)
    assert new_context.metadata["context_options"] == context_options


@pytest.mark.asyncio
async def test_create_context_error_no_driver(action_context):
    """Test CreateContext handles missing driver."""
    action_context.driver = None
    
    create_context = CreateContext()
    result = await create_context(context=action_context)
    
    assert result.is_error()
    assert "No driver found" in str(result.error)


@pytest.mark.asyncio
async def test_create_page_with_switch(action_context, mock_browser_context, mock_page):
    """Test CreatePage creates a new page and switches to it."""
    new_page = create_mock_page("new-page-id")
    
    mock_browser_context.new_page = AsyncMock(return_value=Ok(new_page))
    
    action_context.context = mock_browser_context
    action_context.page_ids = {"existing-page"}
    
    create_page = CreatePage(switch_to=True)
    result = await create_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page == new_page
    assert new_context.page_id is not None
    assert len(new_context.page_ids) == 2
    assert new_context.metadata.get("previous_page_id") == action_context.page_id
    mock_browser_context.new_page.assert_called_once()


@pytest.mark.asyncio
async def test_create_page_without_switch(action_context, mock_browser_context, mock_page):
    """Test CreatePage creates a new page without switching."""
    new_page = create_mock_page("new-page-id")
    
    mock_browser_context.new_page = AsyncMock(return_value=Ok(new_page))
    
    action_context.context = mock_browser_context
    action_context.page = mock_page
    action_context.page_id = "current-page"
    action_context.page_ids = {"current-page"}
    
    create_page = CreatePage(switch_to=False)
    result = await create_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page == mock_page
    assert new_context.page_id == "current-page"
    assert len(new_context.page_ids) == 2
    mock_browser_context.new_page.assert_called_once()


@pytest.mark.asyncio
async def test_create_page_with_nickname(action_context, mock_browser_context):
    """Test CreatePage with a specific nickname."""
    new_page = create_mock_page("custom-nickname")
    new_page.page_id = "custom-nickname"
    
    mock_browser_context.new_page = AsyncMock(return_value=Ok(new_page))
    
    action_context.context = mock_browser_context
    
    create_page = CreatePage(page_nickname="custom-nickname")
    result = await create_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page_id == "custom-nickname"
    assert "custom-nickname" in new_context.page_ids


@pytest.mark.asyncio
async def test_create_page_error_no_context(action_context):
    """Test CreatePage handles missing context."""
    action_context.context = None
    
    create_page = CreatePage()
    result = await create_page(context=action_context)
    
    assert result.is_error()
    assert "No browser context found" in str(result.error)


@pytest.mark.asyncio
async def test_switch_to_existing_page(action_context, mock_browser_context):
    """Test switching to an existing page."""
    page1 = create_mock_page("page-1")
    page1.page_id = "page-1"
    target_page = create_mock_page("target-page")
    target_page.page_id = "target-page"
    
    mock_browser_context.pages = AsyncMock(return_value=Ok([page1, target_page]))
    
    action_context.context = mock_browser_context
    action_context.page = page1
    action_context.page_id = "page-1"
    action_context.page_ids = {"page-1", "target-page"}
    switch_to_page = SwitchToPage(page_id="target-page")
    result = await switch_to_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page_id == "target-page"
    assert new_context.page == target_page
    assert new_context.metadata.get("previous_page_id") == "page-1"


@pytest.mark.asyncio
async def test_switch_to_page_not_tracked(action_context, mock_browser_context):
    """Test switching to a page that's not in tracked pages."""
    action_context.context = mock_browser_context
    action_context.page_ids = {"page-1"}
    
    switch_to_page = SwitchToPage(page_id="untracked-page")
    result = await switch_to_page(context=action_context)
    
    assert result.is_error()
    assert "not found in tracked pages" in str(result.error)


@pytest.mark.asyncio
async def test_switch_to_page_by_index(action_context, mock_browser_context):
    """Test switching to a page by numeric index."""
    page0 = create_mock_page("page-0")
    page1 = create_mock_page("page-1")
    
    mock_browser_context.pages = AsyncMock(return_value=Ok([page0, page1]))
    
    action_context.context = mock_browser_context
    action_context.page = page0
    action_context.page_id = "page-0"
    action_context.page_ids = {"0", "1"}
    
    switch_to_page = SwitchToPage(page_id="1")
    result = await switch_to_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page == page1


@pytest.mark.asyncio
async def test_switch_to_page_error_no_context(action_context):
    """Test SwitchToPage handles missing context."""
    action_context.context = None
    
    switch_to_page = SwitchToPage(page_id="any-page")
    result = await switch_to_page(context=action_context)
    
    assert result.is_error()
    assert "No browser context found" in str(result.error)


@pytest.mark.asyncio
async def test_close_current_page_with_switch(action_context, mock_browser_context):
    """Test closing the current page and switching to another."""
    page1 = create_mock_page("page-1")
    page2 = create_mock_page("page-2")
    
    page1.close = AsyncMock(return_value=Ok(None))
    
    mock_browser_context.pages = AsyncMock(return_value=Ok([page2]))
    
    action_context.context = mock_browser_context
    action_context.page = page1
    action_context.page_id = "page-1"
    action_context.page_ids = {"page-1", "page-2"}
    
    close_page = CloseCurrentPage(switch_to_last=True)
    result = await close_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    page1.close.assert_called_once()
    assert "page-1" not in new_context.page_ids
    assert new_context.page == page2
    assert new_context.metadata.get("closed_page_id") == "page-1"


@pytest.mark.asyncio
async def test_close_last_page(action_context, mock_browser_context):
    """Test closing the last page in a context."""
    page1 = create_mock_page("page-1")
    
    page1.close = AsyncMock(return_value=Ok(None))
    
    mock_browser_context.pages = AsyncMock(return_value=Ok([]))
    
    action_context.context = mock_browser_context
    action_context.page = page1
    action_context.page_id = "page-1"
    action_context.page_ids = {"page-1"}
    
    close_page = CloseCurrentPage(switch_to_last=True)
    result = await close_page(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page is None
    assert new_context.page_id is None
    assert len(new_context.page_ids) == 0


@pytest.mark.asyncio
async def test_close_current_page_error_no_page(action_context):
    """Test CloseCurrentPage handles missing page."""
    action_context.page = None
    
    close_page = CloseCurrentPage()
    result = await close_page(context=action_context)
    
    assert result.is_error()
    assert "No page found" in str(result.error)


@pytest.mark.asyncio
async def test_close_context(action_context, mock_browser_context):
    """Test closing the current context."""
    mock_browser_context.close = AsyncMock(return_value=Ok(None))
    
    action_context.context = mock_browser_context
    action_context.context_id = "test-context"
    
    close_context = CloseContext()
    result = await close_context(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    mock_browser_context.close.assert_called_once()
    assert new_context.context is None
    assert new_context.page is None
    assert new_context.context_id is None
    assert new_context.page_id is None
    assert len(new_context.page_ids) == 0
    assert new_context.metadata.get("closed_context_id") == "test-context"


@pytest.mark.asyncio
async def test_close_context_error_no_context(action_context):
    """Test CloseContext handles missing context."""
    action_context.context = None
    
    close_context = CloseContext()
    result = await close_context(context=action_context)
    
    assert result.is_error()
    assert "No browser context found" in str(result.error)


@pytest.mark.asyncio
async def test_with_new_tab(action_context, mock_browser_context, mock_page):
    """Test WithNewTab creates a new tab and navigates."""
    new_page = create_mock_page("new-tab")
    new_page.goto = AsyncMock(return_value=Ok(None))
    
    mock_browser_context.new_page = AsyncMock(return_value=Ok(new_page))
    
    action_context.context = mock_browser_context
    
    with_new_tab = WithNewTab(url="https://example.com")
    result = await with_new_tab(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page == new_page
    new_page.goto.assert_called_once_with("https://example.com")
    assert new_context.metadata.get("current_url") == "https://example.com"


@pytest.mark.asyncio
async def test_with_new_tab_no_url(action_context, mock_browser_context):
    """Test WithNewTab creates a new tab without navigation."""
    new_page = create_mock_page("new-tab")
    
    mock_browser_context.new_page = AsyncMock(return_value=Ok(new_page))
    
    action_context.context = mock_browser_context
    
    with_new_tab = WithNewTab()
    result = await with_new_tab(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    
    assert new_context.page == new_page
    new_page.goto.assert_not_called()


@pytest.mark.asyncio
async def test_get_all_pages(action_context, mock_browser_context):
    """Test GetAllPages returns list of page IDs."""
    page1 = create_mock_page("page-1")
    page1.page_id = "page-1"
    page2 = create_mock_page("page-2")
    page2.page_id = "page-2"
    
    mock_browser_context.pages = AsyncMock(return_value=Ok([page1, page2]))
    
    action_context.context = mock_browser_context
    
    get_all_pages = GetAllPages()
    result = await get_all_pages(context=action_context)
    
    assert result.is_ok()
    page_ids = result.default_value(None)
    assert page_ids == ["page-1", "page-2"]


@pytest.mark.asyncio
async def test_focus_page(action_context, mock_page):
    """Test FocusPage focuses the current page."""
    mock_page.bring_to_front = AsyncMock(return_value=Ok(None))
    
    action_context.page = mock_page
    action_context.page_id = "test-page"
    
    focus_page = FocusPage()
    result = await focus_page(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == action_context
    mock_page.bring_to_front.assert_called_once()


@pytest.mark.asyncio
async def test_reload_page(action_context, mock_page):
    """Test ReloadPage reloads the current page."""
    mock_page.reload = AsyncMock(return_value=Ok(None))
    
    action_context.page = mock_page
    action_context.page_id = "test-page"
    
    reload_page = ReloadPage(wait_until="load")
    result = await reload_page(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == action_context
    mock_page.reload.assert_called_once()
    call_args = mock_page.reload.call_args[0]
    assert call_args[0].wait_until == "load"


@pytest.mark.asyncio
async def test_get_current_url(action_context, mock_page):
    """Test GetCurrentUrl returns the page URL."""
    mock_page.get_url = AsyncMock(return_value=Ok("https://example.com"))
    
    action_context.page = mock_page
    
    get_url = GetCurrentUrl()
    result = await get_url(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "https://example.com"


@pytest.mark.asyncio
async def test_get_page_title(action_context, mock_page):
    """Test GetPageTitle returns the page title."""
    mock_page.get_title = AsyncMock(return_value=Ok("Example Page"))
    
    action_context.page = mock_page
    
    get_title = GetPageTitle()
    result = await get_title(context=action_context)
    
    assert result.is_ok()
    assert result.default_value(None) == "Example Page"


@pytest.mark.asyncio
async def test_with_metadata_merge(action_context):
    """Test WithMetadata merges metadata."""
    action_context.metadata = {"existing": "value", "override": "old"}
    
    with_metadata = WithMetadata(
        metadata={"new": "value", "override": "new"},
        merge=True
    )
    result = await with_metadata(context=action_context)
    
    assert result.is_ok()
    new_context = result.default_value(None)
    assert new_context.metadata["existing"] == "value"
    assert new_context.metadata["new"] == "value"
    assert new_context.metadata["override"] == "new"


@pytest.mark.asyncio
async def test_with_metadata_replace(action_context):
    """Test WithMetadata replaces metadata."""
    initial_metadata_action = WithMetadata(
        metadata={"existing": "value", "remove": "this"},
        merge=True
    )
    initial_result = await initial_metadata_action(context=action_context)
    assert initial_result.is_ok(), "Failed to set initial metadata"
    context_with_initial_metadata = initial_result.default_value(None)
    assert context_with_initial_metadata is not None

    replace_metadata_action = WithMetadata(
        metadata={"new": "value"},
        merge=False
    )
    result = await replace_metadata_action(context=context_with_initial_metadata)

    assert result.is_ok()
    new_context = result.default_value(None)
    assert new_context.metadata == {"new": "value"}


@pytest.mark.asyncio
async def test_context_management_workflow(action_context, mock_driver):
    """Test a complete workflow using multiple context management actions."""
    context1 = create_mock_context("context-1")
    context2 = create_mock_context("context-2")
    page1 = create_mock_page("page-1")
    page2 = create_mock_page("page-2")
    new_page = create_mock_page("new-page")
    
    mock_driver.new_context = AsyncMock(side_effect=[
        Ok(context1),
        Ok(context2),
    ])
    
    context1.new_page = AsyncMock(return_value=Ok(page1))
    context1.pages = AsyncMock(return_value=Ok([page1]))
    context1.close = AsyncMock(return_value=Ok(None))
    
    context2.new_page = AsyncMock(side_effect=[Ok(page2), Ok(new_page)])
    context2.pages = AsyncMock(return_value=Ok([page2, new_page]))
    
    action_context.driver = mock_driver
    
    create_ctx = CreateContext(create_page=True)
    result1 = await create_ctx(context=action_context)
    assert result1.is_ok()
    ctx1 = result1.default_value(None)
    assert ctx1.context == context1
    assert ctx1.page == page1
    
    create_ctx2 = CreateContext(context_options={"viewport": {"width": 1920, "height": 1080}})
    result2 = await create_ctx2(context=ctx1)
    assert result2.is_ok()
    ctx2 = result2.default_value(None)
    assert ctx2.context == context2
    assert ctx2.metadata["context_options"]["viewport"]["width"] == 1920
    
    create_page = CreatePage(page_nickname="new-page")
    result3 = await create_page(context=ctx2)
    assert result3.is_ok()
    ctx3 = result3.default_value(None)
    assert ctx3.page_id is not None
    assert "new-page" in str(ctx3.page_id) or ctx3.page == new_page
    
    get_pages = GetAllPages()
    pages_result = await get_pages(context=ctx3)
    assert pages_result.is_ok()
    assert len(pages_result.default_value([])) >= 2
    
    with_meta = WithMetadata(metadata={"workflow": "test", "step": 5})
    result5 = await with_meta(context=ctx3)
    assert result5.is_ok()
    ctx5 = result5.default_value(None)
    assert ctx5.metadata["workflow"] == "test"
    
    ctx5.page.get_url = AsyncMock(return_value=Ok("https://example.com"))
    get_url = GetCurrentUrl()
    url_result = await get_url(context=ctx5)
    assert url_result.is_ok()
    assert url_result.default_value(None) == "https://example.com"
    
    ctx5.page.close = AsyncMock(return_value=Ok(None))
    close_page = CloseCurrentPage()
    result7 = await close_page(context=ctx5)
    assert result7.is_ok()
    
    close_ctx = CloseContext()
    result8 = await close_ctx(context=result7.default_value(None))
    assert result8.is_ok()
    final_ctx = result8.default_value(None)
    
    assert final_ctx.context is None
    assert final_ctx.page is None
    assert final_ctx.context_id is None
    assert final_ctx.page_id is None
    assert len(final_ctx.page_ids) == 0


@pytest.mark.asyncio
async def test_multi_tab_workflow(action_context, mock_browser_context, mock_page):
    """Test working with multiple tabs."""
    page1 = create_mock_page("page-1")
    page1.page_id = "page-1"
    page2 = create_mock_page("page-2")
    page2.page_id = "page-2"
    page3 = create_mock_page("page-3")
    page3.page_id = "page-3"

    mock_browser_context.new_page = AsyncMock(side_effect=[Ok(page2), Ok(page3)])

    action_context.context = mock_browser_context
    action_context.page = page1
    action_context.page_id = "page-1"
    action_context.page_ids = {"page-1"}

    mock_browser_context.pages = AsyncMock(side_effect=[
        Ok([page1, page2, page3]),
        Ok([page1, page2, page3])
    ])

    page2.goto = AsyncMock(return_value=Ok(None))
    with_tab = WithNewTab(url="https://example.com")
    result1 = await with_tab(context=action_context)
    assert result1.is_ok()
    ctx1 = result1.default_value(None)
    assert ctx1.page == page2
    page2.goto.assert_called_once_with("https://example.com")
    
    create_page = CreatePage()
    result2 = await create_page(context=ctx1)
    assert result2.is_ok()
    ctx2 = result2.default_value(None)
    assert ctx2.page == page3
    
    get_pages = GetAllPages()
    pages_result = await get_pages(context=ctx2)
    assert pages_result.is_ok()
    assert len(pages_result.default_value([])) == 3
    
    ctx2.page_ids = {"page-1", "page-2", "page-3"}
    switch_page = SwitchToPage(page_id="page-1")
    result4 = await switch_page(context=ctx2)
    assert result4.is_ok()
    ctx4 = result4.default_value(None)
    assert ctx4.page == page1
    assert ctx4.metadata.get("previous_page_id") == ctx2.page_id
    
    page1.bring_to_front = AsyncMock(return_value=Ok(None))
    ctx4.page = page1
    focus = FocusPage()
    result5 = await focus(context=ctx4)
    assert result5.is_ok()
    page1.bring_to_front.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])