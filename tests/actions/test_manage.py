"""
Tests for Silk context management actions module.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from expression.core import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.manage import (
    WithContext, SwitchContext, SwitchPage, CreatePage,
    CloseContext, ClosePage, GetCurrentContext, GetCurrentPage, WithOptions
)
from silk.browsers.manager import BrowserManager
from silk.browsers.context import BrowserContext


# -------------------- Mock Classes for Testing --------------------

class MockBrowserContext(MagicMock):
    """Mock implementation of BrowserContext for testing."""
    
    def __init__(self, id="test-context", *args, **kwargs):
        super().__init__(spec=BrowserContext, *args, **kwargs)
        self.id = id
        self.pages = {}
        self.driver = kwargs.get("driver", MagicMock())
        self.manager = kwargs.get("manager", MagicMock())
        self.options = kwargs.get("options", {})
        self.context_ref = kwargs.get("context_ref", "mock-context-ref")
    
    async def create_page(self, nickname=None):
        """Create a mock page"""
        actual_page_id = nickname or f"page-{len(self.pages) + 1}"
        self.pages[actual_page_id] = MagicMock()
        return Ok(actual_page_id)
    
    async def close_page(self, page_id):
        """Close a mock page"""
        if page_id in self.pages:
            del self.pages[page_id]
            return Ok(None)
        return Error(Exception(f"Page '{page_id}' not found"))
    
    def get_page(self, page_id):
        """Get a mock page"""
        if page_id in self.pages:
            return Ok(self.pages[page_id])
        return Error(Exception(f"Page '{page_id}' not found"))
    
    async def close(self):
        """Close the mock context"""
        self.pages = {}
        return Ok(None)


# -------------------- Fixtures --------------------

@pytest.fixture
def mock_manager():
    """Create a mocked browser manager for testing context management actions."""
    manager = MagicMock(spec=BrowserManager)
    
    # Set up contexts dictionary
    manager.contexts = {}
    manager.drivers = {}
    
    # Mock create_context method
    async def mock_create_context(nickname=None, options=None, create_page=True):
        context_id = nickname or f"context-{len(manager.contexts) + 1}"
        if context_id in manager.contexts:
            return Error(Exception(f"Context with ID '{context_id}' already exists"))
        
        # Create a mock context
        context = MockBrowserContext(id=context_id, manager=manager, options=options)
        manager.contexts[context_id] = context
        manager.drivers[context_id] = MagicMock()
        
        # Create a page if requested
        if create_page:
            await context.create_page()
        
        return Ok(context)
    
    manager.create_context = AsyncMock(side_effect=mock_create_context)
    
    # Mock get_context method
    def mock_get_context(context_id=None):
        if not context_id and manager.contexts:
            context_id = list(manager.contexts.keys())[0]
        
        if not context_id:
            return Error(Exception("No contexts available"))
        
        context = manager.contexts.get(context_id)
        if not context:
            return Error(Exception(f"Context with ID '{context_id}' not found"))
        
        return Ok(context)
    
    manager.get_context = MagicMock(side_effect=mock_get_context)
    
    # Mock close_context method
    async def mock_close_context(context_id):
        if context_id in manager.contexts:
            await manager.contexts[context_id].close()
            del manager.contexts[context_id]
            if context_id in manager.drivers:
                del manager.drivers[context_id]
            return Ok(None)
        return Error(Exception(f"Context with ID '{context_id}' not found"))
    
    manager.close_context = AsyncMock(side_effect=mock_close_context)
    
    return manager


@pytest.fixture
def mock_action_context():
    """Create a mock ActionContext for testing."""
    context = ActionContext(
        browser_manager=MagicMock(spec=BrowserManager),
        context_id="test-context-id",
        page_id="test-page-id"
    )
    return context


# -------------------- WithContext Tests --------------------

@pytest.mark.asyncio
async def test_with_context_creates_new_context(mock_manager):
    """Test WithContext creates a new context when none exists."""
    # Execute
    result = await WithContext(mock_manager)
    
    # Assert
    assert result.is_ok(), f"WithContext failed: {result.error if result.is_error() else ''}"
    action_context = result.default_value(None)
    
    # Verify the context was created
    assert isinstance(action_context, ActionContext)
    assert action_context.browser_manager == mock_manager
    assert action_context.context_id in mock_manager.contexts
    assert action_context.page_id is not None
    
    # Verify create_context was called
    mock_manager.create_context.assert_called_once()


@pytest.mark.asyncio
async def test_with_context_with_specific_id(mock_manager):
    """Test WithContext with a specific context_id."""
    # Execute
    result = await WithContext(mock_manager, context_id="my-custom-context")
    
    # Assert
    assert result.is_ok()
    action_context = result.default_value(None)
    
    # Verify the context was created with the specific ID
    assert action_context.context_id == "my-custom-context"
    assert "my-custom-context" in mock_manager.contexts


@pytest.mark.asyncio
async def test_with_context_gets_existing_context(mock_manager):
    """Test WithContext gets an existing context if it exists."""
    # First create a context
    await mock_manager.create_context(nickname="existing-context")
    
    # Now use WithContext to get it
    result = await WithContext(mock_manager, context_id="existing-context")
    
    # Assert
    assert result.is_ok()
    action_context = result.default_value(None)
    
    # Verify the existing context was used
    assert action_context.context_id == "existing-context"
    
    # Verify create_context was NOT called again (we're reusing the existing context)
    assert mock_manager.create_context.call_count == 1


@pytest.mark.asyncio
async def test_with_context_without_page_creation(mock_manager):
    """Test WithContext with create_page=False."""
    # Execute
    result = await WithContext(mock_manager, create_page=False)
    
    # Assert
    assert result.is_ok()
    action_context = result.default_value(None)
    
    # Verify no page was created
    context = mock_manager.contexts[action_context.context_id]
    assert len(context.pages) == 0
    assert action_context.page_id is None


@pytest.mark.asyncio
async def test_with_context_with_specific_page(mock_manager):
    """Test WithContext with a specific page_id."""
    # First create a context with a page
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    await context.create_page(nickname="existing-page")
    
    # Now use WithContext to get it with the specific page
    result = await WithContext(
        mock_manager, 
        context_id="test-context", 
        page_nickname="existing-page"
    )
    
    # Assert
    assert result.is_ok()
    action_context = result.default_value(None)
    
    # Verify the specific page was used
    assert action_context.context_id == "test-context"
    assert action_context.page_id == "existing-page"


@pytest.mark.asyncio
async def test_with_context_error_handling(mock_manager):
    """Test WithContext handles errors properly."""
    # Make create_context fail
    mock_manager.create_context = AsyncMock(
        return_value=Error(Exception("Failed to create context"))
    )
    
    # Execute
    result = await WithContext(mock_manager)
    
    # Assert
    assert result.is_error()
    assert "Failed to create context" in str(result.error)


# -------------------- SwitchContext Tests --------------------

@pytest.mark.asyncio
async def test_switch_to_existing_context(mock_action_context, mock_manager):
    """Test switching to an existing context."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context to switch to
    await mock_manager.create_context(nickname="target-context")
    
    # Execute
    switch_context = SwitchContext(context_id="target-context")
    result = await switch_context(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the context was switched
    assert new_context.context_id == "target-context"
    assert new_context.page_id is not None  # Should have a default page


@pytest.mark.asyncio
async def test_switch_creates_new_context(mock_action_context, mock_manager):
    """Test switching to a non-existent context creates it."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Execute - switch to a context that doesn't exist yet
    switch_context = SwitchContext(context_id="new-context")
    result = await switch_context(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify a new context was created
    assert new_context.context_id == "new-context"
    assert "new-context" in mock_manager.contexts


@pytest.mark.asyncio
async def test_switch_context_without_page(mock_action_context, mock_manager):
    """Test switching to a context with create_page=False."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Execute
    switch_context = SwitchContext(context_id="new-context", create_page=False)
    result = await switch_context(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify no page was created
    assert new_context.page_id is None
    context = mock_manager.contexts["new-context"]
    assert len(context.pages) == 0


@pytest.mark.asyncio
async def test_switch_context_error_no_manager(mock_action_context):
    """Test SwitchContext handles missing browser manager."""
    # Remove the browser manager
    mock_action_context.browser_manager = None
    
    # Execute
    switch_context = SwitchContext(context_id="any-context")
    result = await switch_context(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "No browser manager found" in str(result.error)


# -------------------- SwitchPage Tests --------------------

@pytest.mark.asyncio
async def test_switch_to_existing_page(mock_action_context, mock_manager):
    """Test switching to an existing page."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context with multiple pages
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    await context.create_page(nickname="page-1")
    await context.create_page(nickname="target-page")
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute
    switch_page = SwitchPage(page_nickname_or_id="target-page")
    result = await switch_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the page was switched
    assert new_context.context_id == "test-context"
    assert new_context.page_id == "target-page"


@pytest.mark.asyncio
async def test_switch_creates_new_page(mock_action_context, mock_manager):
    """Test switching to a non-existent page creates it."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute - switch to a page that doesn't exist yet
    switch_page = SwitchPage(page_nickname_or_id="new-page")
    result = await switch_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify a new page was created
    assert new_context.page_id == "new-page"
    assert "new-page" in context.pages


@pytest.mark.asyncio
async def test_switch_page_no_create(mock_action_context, mock_manager):
    """Test switching to a non-existent page with create_if_missing=False."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute - switch to a page that doesn't exist with create_if_missing=False
    switch_page = SwitchPage(page_nickname_or_id="nonexistent-page", create_if_missing=False)
    result = await switch_page(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "not found and create_if_missing is False" in str(result.error)


@pytest.mark.asyncio
async def test_switch_page_no_page_id(mock_action_context, mock_manager):
    """Test switching with no page_id creates a new page."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute - switch without specifying a page ID
    switch_page = SwitchPage()
    result = await switch_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify a new page was created with auto-generated ID
    assert new_context.page_id != "page-1"
    assert len(context.pages) > 1


# -------------------- CreatePage Tests --------------------

@pytest.mark.asyncio
async def test_create_page_with_auto_id(mock_action_context, mock_manager):
    """Test creating a new page with auto-generated ID."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Get initial page count
    initial_page_count = len(context.pages)
    
    # Execute - create a new page without specifying an ID
    create_page = CreatePage()
    result = await create_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify a new page was created
    assert len(context.pages) > initial_page_count
    assert new_context.page_id != "page-1"
    assert new_context.page_id in context.pages


@pytest.mark.asyncio
async def test_create_page_with_specific_id(mock_action_context, mock_manager):
    """Test creating a new page with a specific ID."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute - create a new page with a specific ID
    create_page = CreatePage(page_nickname_or_id="custom-page")
    result = await create_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the new page was created with the specific ID
    assert new_context.page_id == "custom-page"
    assert "custom-page" in context.pages


@pytest.mark.asyncio
async def test_create_page_error_no_context_id(mock_action_context):
    """Test CreatePage handles missing context ID."""
    # Remove the context ID
    mock_action_context.context_id = None
    
    # Execute
    create_page = CreatePage()
    result = await create_page(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "context ID missing" in str(result.error)


# -------------------- CloseContext and ClosePage Tests --------------------

@pytest.mark.asyncio
async def test_close_context(mock_action_context, mock_manager):
    """Test closing the current context."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context
    context_result = await mock_manager.create_context(nickname="test-context")
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute
    close_context = CloseContext()
    result = await close_context(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    
    # Verify the context was closed
    assert "test-context" not in mock_manager.contexts


@pytest.mark.asyncio
async def test_close_page(mock_action_context, mock_manager):
    """Test closing the current page."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context with multiple pages
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    await context.create_page(nickname="page-1")
    await context.create_page(nickname="page-2")
    
    # Update mock_action_context to use this context and page-1
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute
    close_page = ClosePage()
    result = await close_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the page was closed and we switched to another page
    assert "page-1" not in context.pages
    assert new_context.page_id == "page-2"


@pytest.mark.asyncio
async def test_close_last_page(mock_action_context, mock_manager):
    """Test closing the last page in a context."""
    # Set up the mock_action_context with the mock_manager
    mock_action_context.browser_manager = mock_manager
    
    # Create a context with a single page
    context_result = await mock_manager.create_context(nickname="test-context")
    context = context_result.default_value(None)
    
    # Update mock_action_context to use this context
    mock_action_context.context_id = "test-context"
    mock_action_context.page_id = "page-1"
    
    # Execute
    close_page = ClosePage()
    result = await close_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the page was closed and no new page was selected
    assert len(context.pages) == 0
    assert new_context.page_id is None


@pytest.mark.asyncio
async def test_close_page_error_no_page_id(mock_action_context):
    """Test ClosePage handles missing page ID."""
    # Remove the page ID
    mock_action_context.page_id = None
    
    # Execute
    close_page = ClosePage()
    result = await close_page(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "page ID missing" in str(result.error)


# -------------------- GetCurrentContext and GetCurrentPage Tests --------------------

@pytest.mark.asyncio
async def test_get_current_context(mock_action_context):
    """Test getting the current context ID."""
    # Set context ID
    mock_action_context.context_id = "test-context"
    
    # Execute
    get_context = GetCurrentContext()
    result = await get_context(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "test-context"


@pytest.mark.asyncio
async def test_get_current_page(mock_action_context):
    """Test getting the current page ID."""
    # Set page ID
    mock_action_context.page_id = "test-page"
    
    # Execute
    get_page = GetCurrentPage()
    result = await get_page(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    assert result.default_value(None) == "test-page"


@pytest.mark.asyncio
async def test_get_current_context_error(mock_action_context):
    """Test GetCurrentContext handles missing context ID."""
    # Remove the context ID
    mock_action_context.context_id = None
    
    # Execute
    get_context = GetCurrentContext()
    result = await get_context(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "No context ID" in str(result.error)


@pytest.mark.asyncio
async def test_get_current_page_error(mock_action_context):
    """Test GetCurrentPage handles missing page ID."""
    # Remove the page ID
    mock_action_context.page_id = None
    
    # Execute
    get_page = GetCurrentPage()
    result = await get_page(context=mock_action_context)
    
    # Assert
    assert result.is_error()
    assert "No page ID" in str(result.error)


# -------------------- WithOptions Tests --------------------

@pytest.mark.asyncio
async def test_with_options(mock_action_context):
    """Test updating context with additional options."""
    # Initial metadata should be empty
    assert mock_action_context.metadata == {}
    
    # Execute
    with_options = WithOptions(options={"test_key": "test_value", "timeout": 5000})
    result = await with_options(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify the metadata was updated
    assert new_context.metadata["test_key"] == "test_value"
    assert new_context.metadata["timeout"] == 5000


@pytest.mark.asyncio
async def test_with_options_preserves_existing(mock_action_context):
    """Test WithOptions preserves existing metadata and adds new values."""
    # Add some initial metadata
    mock_action_context.metadata = {"existing_key": "existing_value"}
    
    # Execute
    with_options = WithOptions(options={"new_key": "new_value"})
    result = await with_options(context=mock_action_context)
    
    # Assert
    assert result.is_ok()
    new_context = result.default_value(None)
    
    # Verify both old and new metadata exists
    assert new_context.metadata["existing_key"] == "existing_value"
    assert new_context.metadata["new_key"] == "new_value"


# -------------------- Integration Tests --------------------

@pytest.mark.asyncio
async def test_context_management_workflow(mock_manager):
    """Test a complete workflow using multiple context management actions."""
    # 1. Start with WithContext to create initial context
    with_context_result = await WithContext(mock_manager)
    assert with_context_result.is_ok()
    context1 = with_context_result.default_value(None)
    context1_id = context1.context_id
    
    # 2. Switch to a new context
    switch_context = SwitchContext(context_id="second-context")
    switch_result = await switch_context(context=context1)
    assert switch_result.is_ok()
    context2 = switch_result.default_value(None)
    assert context2.context_id == "second-context"
    
    # 3. Create a new page in the second context
    create_page = CreatePage(page_nickname_or_id="new-page")
    create_result = await create_page(context=context2)
    assert create_result.is_ok()
    context2_with_new_page = create_result.default_value(None)
    assert context2_with_new_page.page_id == "new-page"
    
    # 4. Switch back to the first context
    switch_back = SwitchContext(context_id=context1_id)
    switch_back_result = await switch_back(context=context2_with_new_page)
    assert switch_back_result.is_ok()
    back_to_context1 = switch_back_result.default_value(None)
    assert back_to_context1.context_id == context1_id
    
    # 5. Add options to the context
    with_options = WithOptions(options={"timeout": 10000})
    options_result = await with_options(context=back_to_context1)
    assert options_result.is_ok()
    context_with_options = options_result.default_value(None)
    assert context_with_options.metadata["timeout"] == 10000
    
    # 6. Get current page and context IDs
    get_context = GetCurrentContext()
    get_page = GetCurrentPage()
    
    context_id_result = await get_context(context=context_with_options)
    page_id_result = await get_page(context=context_with_options)
    
    assert context_id_result.is_ok()
    assert page_id_result.is_ok()
    assert context_id_result.default_value(None) == context1_id
    
    # 7. Close current page
    close_page = ClosePage()
    close_page_result = await close_page(context=context_with_options)
    assert close_page_result.is_ok()
    
    # 8. Close first context
    close_context = CloseContext()
    close_context_result = await close_context(context=context_with_options)
    assert close_context_result.is_ok()
    
    # Verify the first context was closed but the second still exists
    assert context1_id not in mock_manager.contexts
    assert "second-context" in mock_manager.contexts


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])