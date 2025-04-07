from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.actions.context import (
    CloseContext,
    ClosePage,
    CreateContext,
    CreatePage,
    SwitchContext,
)
from silk.models.browser import ActionContext

# Mock Actions for testing


class ReturnValueAction(Action[str]):
    """Action that returns a specific value"""

    def __init__(self, value: str):
        self.value = value

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        return Ok(self.value)


class ReturnNoneAction(Action[None]):
    """Action that returns None (like many browser actions)"""

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        return Ok(None)


class FailingAction(Action[Any]):
    """Action that always fails with an error"""

    def __init__(self, error_message: str = "Action failed"):
        self.error_message = error_message

    async def execute(self, context: ActionContext) -> Result[Any, Exception]:
        return Error(Exception(self.error_message))


class TransformAction(Action[str]):
    """Action that transforms an input value"""

    def __init__(self, prefix: str = "transformed_"):
        self.prefix = prefix

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        return Ok(f"{self.prefix}value")


class AcceptNoneReturnValueAction(Action[str]):
    """Action that accepts None as input but returns a value"""

    def __init__(self, default_value: str = "default"):
        self.default_value = default_value

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        return Ok(self.default_value)


# Let's create mock browser actions for testing
class Navigate(Action[None]):
    """Mock Navigate action that returns None"""

    def __init__(self, url: str):
        self.url = url

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("Page not found"))

        goto_result = await page.goto(self.url)
        return goto_result


class Click(Action[None]):
    """Mock Click action that returns None"""

    def __init__(self, selector: str):
        self.selector = selector

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("Page not found"))

        click_result = await page.click(self.selector)
        return click_result


class Fill(Action[None]):
    """Mock Fill action that returns None"""

    def __init__(self, selector: str, value: str):
        self.selector = selector
        self.value = value

    async def execute(self, context: ActionContext) -> Result[None, Exception]:
        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("Page not found"))

        fill_result = await page.fill(self.selector, self.value)
        return fill_result


class ExtractText(Action[str]):
    """Mock ExtractText action that returns a string value"""

    def __init__(self, selector: str):
        self.selector = selector

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        # A simplified version that returns a fixed string for testing
        return Ok("Extracted Text")


class TestActionChaining:
    @pytest.mark.asyncio
    async def test_and_then_with_value_actions(self, action_context):
        """Test chaining actions that both return values"""
        # Arrange
        first_action = ReturnValueAction("first")
        second_action = ReturnValueAction("second")

        # Act
        chained_action = first_action.and_then(lambda val: second_action)
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "second"

    @pytest.mark.asyncio
    async def test_and_then_with_transform(self, action_context):
        """Test chaining with a transformation of the first result"""
        # Arrange
        first_action = ReturnValueAction("first")

        # Act - create a transform action that uses the value
        chained_action = first_action.and_then(
            lambda val: ReturnValueAction(f"transformed_{val}")
        )
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "transformed_first"

    @pytest.mark.asyncio
    async def test_and_then_with_none_value(self, action_context):
        """Test chaining from an action that returns None to another action"""
        # Arrange
        first_action = ReturnNoneAction()
        second_action = AcceptNoneReturnValueAction("after_none")

        # Act
        chained_action = first_action.and_then(lambda _: second_action)
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "after_none"

    @pytest.mark.asyncio
    async def test_rshift_operator_with_actions(self, action_context):
        """Test the >> operator for chaining actions"""
        # Arrange
        first_action = ReturnValueAction("first")
        second_action = ReturnValueAction("second")

        # Act
        chained_action = first_action >> second_action
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "second"

    @pytest.mark.asyncio
    async def test_rshift_operator_with_none_values(self, action_context):
        """Test the >> operator with actions that return None"""
        # Arrange
        first_action = ReturnNoneAction()
        second_action = ReturnNoneAction()
        third_action = AcceptNoneReturnValueAction("final")

        # Act
        chained_action = first_action >> second_action >> third_action
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "final"

    @pytest.mark.asyncio
    async def test_error_propagation_in_chain(self, action_context):
        """Test that errors are properly propagated through the chain"""
        # Arrange
        first_action = ReturnValueAction("first")
        failing_action = FailingAction("Something went wrong")
        third_action = ReturnValueAction("third")

        # Act
        chained_action = first_action >> failing_action >> third_action
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_error()
        assert str(result.error) == "Something went wrong"

    @pytest.mark.asyncio
    async def test_map_after_none_value(self, action_context):
        """Test using map after an action that returns None"""
        # Arrange
        none_action = ReturnNoneAction()

        # Act
        # This would fail with the old implementation that required non-None values
        mapped_action = none_action.map(lambda _: "mapped_value")
        result = await mapped_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "mapped_value"

    @pytest.mark.asyncio
    async def test_complex_action_chain(self, action_context):
        """Test a more complex chain of actions with mixed return types"""
        # Arrange
        first_action = ReturnValueAction("first")
        none_action = ReturnNoneAction()
        transform_action = TransformAction()

        # Act - create a complex chain
        chained_action = first_action >> none_action >> transform_action
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "transformed_value"

    # Test with context actions

    class MockCreateContextAction(Action[ActionContext]):
        """Mock of CreateContext action that returns a new ActionContext"""

        async def execute(
            self, context: ActionContext
        ) -> Result[ActionContext, Exception]:
            new_context = context.derive(context_id="new-context-id")
            return Ok(new_context)

    class MockSwitchContextAction(Action[None]):
        """Mock of SwitchContext action that returns None"""

        async def execute(self, context: ActionContext) -> Result[None, Exception]:
            # This would update context.context_id in real implementation
            return Ok(None)

    @pytest.mark.asyncio
    async def test_context_action_chaining(self, action_context):
        """Test chaining context actions with browser actions"""
        # Arrange
        create_context = self.MockCreateContextAction()
        switch_context = self.MockSwitchContextAction()
        navigate_action = ReturnNoneAction()  # Mock for Navigate action

        # Act
        chained_action = create_context >> switch_context >> navigate_action
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        # Result should be None from the last action
        assert result.default_value("not none") is None

    @pytest.mark.asyncio
    async def test_rshift_operator_with_function(self, action_context):
        """Test the >> operator with a function (map behavior)"""
        # Arrange
        value_action = ReturnValueAction("test")

        # Act
        chained_action = value_action >> (lambda s: s.upper())
        result = await chained_action.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "TEST"

    @pytest.mark.asyncio
    async def test_browser_action_sequence(self, action_context, mock_browser_page):
        """Test a typical browser action sequence with the >> operator"""
        # Arrange
        # First make sure context.get_page() returns our mock page
        action_context.get_page = AsyncMock(return_value=Ok(mock_browser_page))

        # Create our action sequence
        action_sequence = (
            Navigate("https://example.com")
            >> Click("#login-button")
            >> Fill("#username", "testuser")
            >> Fill("#password", "password")
            >> Click("#submit")
            >> ExtractText("#result")
        )

        # Act
        result = await action_sequence.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "Extracted Text"

        # Verify each mock method was called with correct arguments
        mock_browser_page.goto.assert_called_once_with("https://example.com")
        mock_browser_page.click.assert_called_with("#submit")  # Called twice
        mock_browser_page.fill.assert_called_with("#password", "password")

    @pytest.mark.asyncio
    async def test_context_action_sequence(self, mock_browser_manager, action_context):
        """Test context management actions in a sequence"""
        # Arrange - patch the BrowserManager methods to return our mocks
        # We'll manually set up the derived context to test the chain flow

        # Configure the CreateContext action
        create_context_result = action_context.derive(context_id="new-context-id")
        mock_browser_manager.create_context = AsyncMock(
            return_value=Ok(create_context_result)
        )

        # Create our action sequence with context management
        action_sequence = (
            CreateContext("test-context")
            >> CreatePage("test-page")
            >> Navigate("https://example.com")
            >> SwitchContext("another-context")
            >> ClosePage()
            >> CloseContext()
        )

        # Act
        result = await action_sequence.execute(action_context)

        # Assert
        assert result.is_ok()

        # Verify the context operations were called
        mock_browser_manager.create_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_browser_sequence(self, action_context):
        """Test error handling in a browser action sequence"""
        # Arrange
        # Make get_page return an error
        action_context.get_page = AsyncMock(
            return_value=Error(Exception("Page not available"))
        )

        # Create action sequence
        action_sequence = (
            Navigate("https://example.com")
            >> Click("#button")
            >> ExtractText("#result")
        )

        # Act
        result = await action_sequence.execute(action_context)

        # Assert
        assert result.is_error()
        assert "Page not available" in str(result.error)

    @pytest.mark.asyncio
    async def test_mixed_return_types_in_sequence(
        self, action_context, mock_browser_page
    ):
        """Test a sequence with mixed return type actions"""
        # Arrange
        action_context.get_page = AsyncMock(return_value=Ok(mock_browser_page))

        # Custom action that transforms the context
        class AddMetadata(Action[ActionContext]):
            async def execute(
                self, context: ActionContext
            ) -> Result[ActionContext, Exception]:
                new_context = context.derive(metadata={"test": "value"})
                return Ok(new_context)

        # Create action sequence with mixed return types
        action_sequence = (
            AddMetadata()  # Returns ActionContext
            >> Navigate("https://example.com")  # Returns None
            >> ExtractText("#content")  # Returns string
            >> (lambda text: text.upper())  # Transform function
        )

        # Act
        result = await action_sequence.execute(action_context)

        # Assert
        assert result.is_ok()
        assert result.default_value(None) == "EXTRACTED TEXT"

    @pytest.mark.asyncio
    async def test_create_and_switch_context(
        self, action_context, mock_browser_manager, mock_browser_context
    ):
        """Test creating a context and then switching to it"""
        # Arrange
        # Setup mocks to return appropriate values
        new_context = mock_browser_context
        new_context.id = "new-context-id"

        mock_browser_manager.create_context = AsyncMock(return_value=Ok(new_context))
        mock_browser_manager.get_context = MagicMock(return_value=Ok(new_context))

        # Create action sequence
        action_sequence = CreateContext("test-context") >> SwitchContext(
            "new-context-id"
        )

        # Act
        result = await action_sequence.execute(action_context)

        # Assert
        assert result.is_ok()
        mock_browser_manager.create_context.assert_called_once()
        mock_browser_manager.get_context.assert_called_with("new-context-id")
