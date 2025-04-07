"""
Tests for the ActionContext class.
"""

import pytest
from expression.core import Error, Ok

from silk.models.browser import ActionContext


class TestActionContext:
    """Test suite for the ActionContext class."""

    def test_initialization(self, mock_browser_manager):
        """Test that ActionContext is initialized correctly."""
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="test-context",
            page_id="test-page",
            retry_count=1,
            max_retries=3,
            retry_delay_ms=100,
            timeout_ms=5000,
        )

        assert context.browser_manager == mock_browser_manager
        assert context.context_id == "test-context"
        assert context.page_id == "test-page"
        assert context.retry_count == 1
        assert context.max_retries == 3
        assert context.retry_delay_ms == 100
        assert context.timeout_ms == 5000
        assert context.metadata == {}
        assert context.parent_context is None

    def test_initialization_with_metadata(self, mock_browser_manager):
        """Test that ActionContext is initialized correctly with metadata."""
        metadata = {"key": "value", "another_key": 123}
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="test-context",
            page_id="test-page",
            metadata=metadata,
        )

        assert context.metadata == metadata

    def test_initialization_with_parent_context(
        self, mock_browser_manager, action_context
    ):
        """Test that ActionContext is initialized correctly with a parent context."""
        child_context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="child-context",
            page_id="child-page",
            parent_context=action_context,
        )

        assert child_context.parent_context == action_context

    @pytest.mark.asyncio
    async def test_get_page_success(
        self, mock_browser_manager, mock_browser_context, mock_browser_page
    ):
        """Test getting a page from the context successfully."""
        # Set up mocks
        mock_browser_manager.get_context.return_value = Ok(mock_browser_context)
        mock_browser_context.get_page.return_value = Ok(mock_browser_page)

        # Create context
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="mock-context-id",
            page_id="mock-page-id",
        )

        # Get page
        result = await context.get_page()

        # Assert
        assert result.is_ok()
        value = result.default_value(None)
        if value is None:
            pytest.fail("Failed to get page")
        assert value == mock_browser_page
        mock_browser_manager.get_context.assert_called_once_with("mock-context-id")
        mock_browser_context.get_page.assert_called_once_with("mock-page-id")

    @pytest.mark.asyncio
    async def test_get_page_missing_required_fields(self):
        """Test getting a page fails when required fields are missing."""
        # Create context without required fields
        context = ActionContext()

        # Get page
        result = await context.get_page()

        # Assert
        assert result.is_error()
        assert "missing required browser_manager, context_id, or page_id" in str(
            result.error
        )

    @pytest.mark.asyncio
    async def test_get_page_context_not_found(self, mock_browser_manager):
        """Test getting a page fails when the context is not found."""
        # Set up mocks
        mock_browser_manager.get_context.return_value = Error(
            Exception("Context not found")
        )

        # Create context
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="non-existent-context",
            page_id="test-page",
        )

        # Get page
        result = await context.get_page()

        # Assert
        assert result.is_error()
        assert "Context not found" in str(result.error)
        mock_browser_manager.get_context.assert_called_once_with("non-existent-context")

    @pytest.mark.asyncio
    async def test_get_driver_success(self, mock_browser_manager, mock_browser_driver):
        """Test getting a driver from the context successfully."""
        # Set up mocks
        mock_browser_manager.drivers = {"mock-context-id": mock_browser_driver}

        # Create context
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="mock-context-id",
            page_id="mock-page-id",
        )

        # Get driver
        result = await context.get_driver()

        # Assert
        assert result.is_ok()
        value = result.default_value(None)
        if value is None:
            pytest.fail("Failed to get driver")
        assert value == mock_browser_driver

    @pytest.mark.asyncio
    async def test_get_driver_missing_required_fields(self):
        """Test getting a driver fails when required fields are missing."""
        # Create context without required fields
        context = ActionContext()

        # Get driver
        result = await context.get_driver()

        # Assert
        assert result.is_error()
        assert "missing required browser_manager or context_id" in str(result.error)

    @pytest.mark.asyncio
    async def test_get_driver_not_found(self, mock_browser_manager):
        """Test getting a driver fails when the driver is not found."""
        # Set up mocks
        mock_browser_manager.drivers = {}

        # Create context
        context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="non-existent-context",
            page_id="test-page",
        )

        # Get driver
        result = await context.get_driver()

        # Assert
        assert result.is_error()
        assert "No driver found for context ID" in str(result.error)

    def test_derive_context(self, mock_browser_manager):
        """Test deriving a new context from an existing one."""
        # Create original context
        original_context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="original-context",
            page_id="original-page",
            retry_count=1,
            max_retries=3,
            retry_delay_ms=100,
            timeout_ms=5000,
            metadata={"original": True},
        )

        # Derive a new context with some changes
        derived_context = original_context.derive(
            context_id="derived-context",
            page_id="derived-page",
            max_retries=5,
            metadata={"derived": True},
        )

        # Assert
        assert derived_context.browser_manager == original_context.browser_manager
        assert derived_context.context_id == "derived-context"
        assert derived_context.page_id == "derived-page"
        assert derived_context.retry_count == original_context.retry_count
        assert derived_context.max_retries == 5
        assert derived_context.retry_delay_ms == original_context.retry_delay_ms
        assert derived_context.timeout_ms == original_context.timeout_ms
        assert derived_context.parent_context == original_context
        assert derived_context.metadata == {"original": True, "derived": True}

    def test_derive_context_with_parent_override(
        self, mock_browser_manager, action_context
    ):
        """Test deriving a context with a parent override."""
        # Create original context
        original_context = ActionContext(
            browser_manager=mock_browser_manager,
            context_id="original-context",
            page_id="original-page",
        )

        # Derive with a specific parent
        derived_context = original_context.derive(parent_context=action_context)

        # Assert
        assert derived_context.parent_context == action_context
