"""
Tests for the BrowserManager class.
"""

from unittest.mock import MagicMock, patch

import pytest
from expression.core import Error, Ok

from silk.browsers.manager import BrowserManager
from silk.browsers.types import BrowserOptions


async def async_ok(value):
    return Ok(value)


async def async_error(error):
    return Error(error)


class TestBrowserManager:
    """Test suite for the BrowserManager class."""

    def test_initialization(self):
        """Test that BrowserManager is initialized correctly."""
        # Default initialization
        manager = BrowserManager()
        assert manager.driver_type == "playwright"
        assert isinstance(manager.default_options, BrowserOptions)
        assert manager.drivers == {}
        assert manager.contexts == {}
        assert manager.default_context_id is None

        # Custom initialization
        options = BrowserOptions(headless=False, timeout=10000)
        manager = BrowserManager(driver_type="playwright", default_options=options)
        assert manager.driver_type == "playwright"
        assert manager.default_options == options

    @pytest.mark.asyncio
    async def test_create_context_success(self):
        """Test creating a browser context successfully."""
        with patch("silk.browsers.manager.create_driver") as mock_create_driver:
            # Set up mock driver with awaitable results
            mock_driver = MagicMock()
            mock_driver.launch.return_value = async_ok(None)
            mock_driver.create_context.return_value = async_ok("mock-context-ref")
            mock_create_driver.return_value = mock_driver

            # Create manager
            manager = BrowserManager()

            # Create context
            result = await manager.create_context(
                nickname="test-context", create_page=False
            )

            # Assert
            assert result.is_ok()
            context = result.default_value(None)
            if context is None:
                pytest.fail("Failed to create context")
            assert context.id == "test-context"
            assert context.driver == mock_driver
            assert context.manager == manager
            assert context.context_ref == "mock-context-ref"
            assert manager.contexts["test-context"] == context
            assert manager.drivers["test-context"] == mock_driver
            assert manager.default_context_id == "test-context"

            # Verify method calls
            mock_create_driver.assert_called_once_with(
                "playwright", manager.default_options
            )
            mock_driver.launch.assert_called_once()
            mock_driver.create_context.assert_called_once_with(None)  # No options

    @pytest.mark.asyncio
    async def test_create_context_with_page(self):
        """Test creating a browser context with a page."""
        with patch("silk.browsers.manager.create_driver") as mock_create_driver:
            # Set up mocks with awaitable results
            mock_driver = MagicMock()
            mock_driver.launch.return_value = async_ok(None)
            mock_driver.create_context.return_value = async_ok("mock-context-ref")
            mock_create_driver.return_value = mock_driver

            # Mock the BrowserContext.create_page method
            mock_page = MagicMock()
            mock_context = MagicMock()
            mock_context.create_page.return_value = async_ok(mock_page)

            # Patch BrowserContext to return our mock
            with patch(
                "silk.browsers.manager.BrowserContext", return_value=mock_context
            ):
                # Create manager
                manager = BrowserManager()

                # Create context with page
                result = await manager.create_context(
                    nickname="test-context", create_page=True
                )

                # Assert
                assert result.is_ok()
                context = result.default_value(None)
                if context is None:
                    pytest.fail("Failed to create context")
                assert context == mock_context
                mock_context.create_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_context_existing_nickname(self, mock_browser_context):
        """Test creating a context with an existing nickname fails."""
        # Create manager with existing context
        manager = BrowserManager()
        manager.contexts = {"test-context": mock_browser_context}

        # Create context with same nickname
        result = await manager.create_context(nickname="test-context")

        # Assert
        assert result.is_error()
        assert "Context with ID 'test-context' already exists" in str(result.error)

    @pytest.mark.asyncio
    async def test_create_context_driver_launch_failure(self):
        """Test handling driver launch failure when creating a context."""
        with patch("silk.browsers.manager.create_driver") as mock_create_driver:
            # Set up mock driver with launch failure
            mock_driver = MagicMock()
            mock_driver.launch.return_value = async_error(
                Exception("Failed to launch browser")
            )
            mock_create_driver.return_value = mock_driver

            # Create manager
            manager = BrowserManager()

            # Create context
            result = await manager.create_context(nickname="test-context")

            # Assert
            assert result.is_error()
            assert "Failed to launch browser" in str(result.error)
            assert "test-context" not in manager.contexts
            assert "test-context" not in manager.drivers

    @pytest.mark.asyncio
    async def test_create_context_create_context_failure(self):
        """Test handling create_context failure."""
        with patch("silk.browsers.manager.create_driver") as mock_create_driver:
            # Set up mock driver with create_context failure
            mock_driver = MagicMock()
            mock_driver.launch.return_value = async_ok(None)
            mock_driver.create_context.return_value = async_error(
                Exception("Failed to create context")
            )
            mock_create_driver.return_value = mock_driver

            # Create manager
            manager = BrowserManager()

            # Create context
            result = await manager.create_context(nickname="test-context")

            # Assert
            assert result.is_error()
            assert "Failed to create context" in str(result.error)
            assert "test-context" not in manager.contexts
            # The driver is still in drivers dict because it launched successfully
            assert manager.drivers["test-context"] == mock_driver

    def test_get_context_success(self, mock_browser_context):
        """Test getting a browser context successfully."""
        # Create manager with existing context
        manager = BrowserManager()
        manager.contexts = {"test-context": mock_browser_context}
        manager.default_context_id = "test-context"
        
        # Ensure the mock has a nickname attribute
        mock_browser_context.nickname = "test-context"
        
        # Get context by ID
        result = manager.get_context("test-context")
        assert result.is_ok()
        context = result.default_value(None)
        if context is None:
            pytest.fail("Failed to get context")
        assert context == mock_browser_context

        # Get default context
        result = manager.get_context()
        assert result.is_ok()
        context = result.default_value(None)
        if context is None:
            pytest.fail("Failed to get context")
        assert context == mock_browser_context

    @pytest.mark.asyncio
    async def test_close_context_success(
        self, mock_browser_context, mock_browser_driver
    ):
        """Test closing a browser context successfully."""
        # Create manager with existing context and driver
        manager = BrowserManager()
        manager.contexts = {"test-context": mock_browser_context}
        manager.drivers = {"test-context": mock_browser_driver}
        manager.default_context_id = "test-context"
        
        # Ensure the mock has a nickname attribute
        mock_browser_context.nickname = "test-context"
        
        # Set up mocks with awaitable results
        mock_browser_context.close.return_value = async_ok(None)
        mock_browser_driver.close.return_value = async_ok(None)

        # Close context
        result = await manager.close_context("test-context")

        # Assert
        assert result.is_ok()
        assert "test-context" not in manager.contexts
        assert "test-context" not in manager.drivers
        assert manager.default_context_id is None
        mock_browser_context.close.assert_called_once()
        mock_browser_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_context_not_found(self):
        """Test closing a non-existent context."""
        # Create manager with no contexts
        manager = BrowserManager()

        # Close non-existent context
        result = await manager.close_context("non-existent")

        # Assert
        assert result.is_error()
        assert "Context with ID 'non-existent' not found" in str(result.error)

    @pytest.mark.asyncio
    async def test_close_all_contexts(self, mock_browser_context, mock_browser_driver):
        """Test closing all browser contexts."""
        # Create manager with multiple contexts
        manager = BrowserManager()

        # Add first context with awaitable close result
        context1 = MagicMock()
        context1.id = "context1"
        context1.close.return_value = async_ok(None)
        manager.contexts["context1"] = context1
        manager.drivers["context1"] = MagicMock()
        manager.drivers["context1"].close.return_value = async_ok(None)

        # Add second context with awaitable close result
        context2 = MagicMock()
        context2.id = "context2"
        context2.close.return_value = async_ok(None)
        manager.contexts["context2"] = context2
        manager.drivers["context2"] = MagicMock()
        manager.drivers["context2"].close.return_value = async_ok(None)

        manager.default_context_id = "context1"

        # Close all
        result = await manager.close_all()

        # Assert
        assert result.is_ok()
        assert manager.contexts == {}
        assert manager.drivers == {}
        assert manager.default_context_id is None
        context1.close.assert_called_once()
        context2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_all_with_errors(self):
        """Test closing all contexts when some close operations fail."""
        # Create manager with multiple contexts
        manager = BrowserManager()

        # Add first context - will succeed
        context1 = MagicMock()
        context1.id = "context1"
        context1.close.return_value = async_ok(None)
        manager.contexts["context1"] = context1
        manager.drivers["context1"] = MagicMock()
        manager.drivers["context1"].close.return_value = async_ok(None)

        # Add second context - will fail
        context2 = MagicMock()
        context2.id = "context2"
        context2.close.return_value = async_error(Exception("Failed to close context"))
        manager.contexts["context2"] = context2
        manager.drivers["context2"] = MagicMock()
        manager.drivers["context2"].close.return_value = async_ok(None)

        manager.default_context_id = "context1"

        # Close all
        result = await manager.close_all()

        # Assert
        assert result.is_error()
        assert "Errors closing contexts" in str(result.error)
        context1.close.assert_called_once()
        context2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test using the session context manager."""
        # Create manager
        manager = BrowserManager()

        # Mock create_context and close_context
        mock_context = MagicMock()
        mock_context.id = "session-context"

        original_create_context = manager.create_context
        original_close_context = manager.close_context

        async def mock_create_context(*args, **kwargs):
            return Ok(mock_context)

        async def mock_close_context(*args, **kwargs):
            return Ok(None)

        manager.create_context = mock_create_context
        manager.close_context = mock_close_context

        try:
            # Use session context manager
            async with manager.session(nickname="session-context") as context:
                assert context == mock_context
        finally:
            # Restore original methods
            manager.create_context = original_create_context
            manager.close_context = original_close_context

    @pytest.mark.asyncio
    async def test_session_with_existing_context(self):
        """Test using the session context manager with an existing context."""
        # Create manager with existing context
        manager = BrowserManager()
        mock_context = MagicMock()
        mock_context.id = "existing-context"
        manager.contexts = {"existing-context": mock_context}

        # Mock get_context
        original_get_context = manager.get_context

        def mock_get_context(*args, **kwargs):
            return Ok(mock_context)

        manager.get_context = mock_get_context

        # Mock close_context to verify it's not called
        close_context_called = False

        async def mock_close_context(*args, **kwargs):
            nonlocal close_context_called
            close_context_called = True
            return Ok(None)

        original_close_context = manager.close_context
        manager.close_context = mock_close_context

        try:
            # Use session context manager with existing context
            async with manager.session(nickname="existing-context") as context:
                assert context == mock_context

            # Verify close_context was not called
            assert not close_context_called
        finally:
            # Restore original methods
            manager.get_context = original_get_context
            manager.close_context = original_close_context

    @pytest.mark.asyncio
    async def test_session_error_handling(self):
        """Test error handling in the session context manager."""
        # Create manager
        manager = BrowserManager()

        # Mock create_context to succeed
        mock_context = MagicMock()
        mock_context.id = "session-context"

        original_create_context = manager.create_context
        original_close_context = manager.close_context

        async def mock_create_context(*args, **kwargs):
            return Ok(mock_context)

        close_context_called = False

        async def mock_close_context(*args, **kwargs):
            nonlocal close_context_called
            close_context_called = True
            return Ok(None)

        manager.create_context = mock_create_context
        manager.close_context = mock_close_context

        try:
            # Use session context manager with an exception
            with pytest.raises(RuntimeError, match="Test exception"):
                async with manager.session(nickname="session-context") as context:
                    assert context == mock_context
                    raise RuntimeError("Test exception")

            # Verify close_context was called despite the exception
            assert close_context_called
        finally:
            # Restore original methods
            manager.create_context = original_create_context
            manager.close_context = original_close_context
