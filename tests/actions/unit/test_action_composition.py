import asyncio
from unittest.mock import MagicMock

import pytest
from expression.collections import Block
from expression.core import Error, Ok

from silk.actions.base import Action, create_action

# Import the composition functions
from silk.actions.composition import compose, fallback, parallel, pipe, sequence
from silk.actions.input import Click, Fill
from silk.models.browser import ActionContext


class TestActionBaseComposition:
    @pytest.mark.asyncio
    async def test_map_success(self, action_context, mock_element_handle):
        """Test mapping a successful action result."""

        # Create a mock action that always succeeds
        class SuccessAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Ok("success")

        # Map the result to uppercase
        def to_uppercase(x):
            return x.upper()

        mapped_action = SuccessAction().map(to_uppercase)

        # Execute and verify
        result = await mapped_action.execute(action_context)

        assert result.is_ok()
        assert result.default_value(None) == "SUCCESS"

    @pytest.mark.asyncio
    async def test_map_error(self, action_context):
        """Test mapping an action that returns an error."""

        # Create a mock action that always fails
        class FailingAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Error(Exception("Deliberate error"))

        # Even though we map, the error should propagate
        def to_uppercase(x):
            return x.upper()

        mapped_action = FailingAction().map(to_uppercase)

        # Execute and verify
        result = await mapped_action.execute(action_context)

        assert result.is_error()
        assert "Deliberate error" in str(result.error)

    @pytest.mark.asyncio
    async def test_and_then_success(
        self, action_context, mock_browser_page, mock_element_handle
    ):
        """Test chaining actions with and_then."""
        # Setup mock behaviors
        mock_browser_page.query_selector.return_value = Ok(mock_element_handle)
        mock_element_handle.get_text.return_value = Ok("input text")

        # Create a sequence of actions
        class GetElementAction(Action[str]):
            async def execute(self, context: ActionContext):
                # Simulate getting an element text
                return Ok("input field")

        def create_fill_action(element_id):
            return Fill(f"#{element_id}", "test value")

        # Chain the actions
        chained_action = GetElementAction().and_then(create_fill_action)

        # Execute and verify
        result = await chained_action.execute(action_context)

        assert result.is_ok()
        mock_browser_page.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_and_then_first_fails(self, action_context):
        """Test and_then when the first action fails."""

        # Create a mock action that always fails
        class FailingAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Error(Exception("First action failed"))

        # This second action should never execute
        second_action_mock = MagicMock()

        # Chain the actions
        def second_action(_):
            return second_action_mock

        chained_action = FailingAction().and_then(second_action)

        # Execute and verify
        result = await chained_action.execute(action_context)

        assert result.is_error()
        assert "First action failed" in str(result.error)
        assert not second_action_mock.called

    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self, action_context):
        """Test retry logic with eventual success."""
        # Create a counter and a mock action that fails twice then succeeds
        attempts = [0]

        class EventuallySuccessAction(Action[str]):
            async def execute(self, context: ActionContext):
                attempts[0] += 1
                if attempts[0] < 3:
                    return Error(Exception(f"Failure attempt {attempts[0]}"))
                return Ok("Success on attempt 3")

        # Add retry logic
        action_with_retry = EventuallySuccessAction().retry(max_attempts=3, delay_ms=10)

        # Execute and verify
        result = await action_with_retry.execute(action_context)

        assert result.is_ok()
        assert attempts[0] == 3
        assert result.default_value(None) == "Success on attempt 3"

    @pytest.mark.asyncio
    async def test_retry_all_failures(self, action_context):
        """Test retry logic when all attempts fail."""

        # Create a mock action that always fails
        class AlwaysFailingAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Error(Exception("Always fails"))

        # Add retry logic
        action_with_retry = AlwaysFailingAction().retry(max_attempts=3, delay_ms=10)

        # Execute and verify
        result = await action_with_retry.execute(action_context)

        assert result.is_error()
        assert "Always fails" in str(result.error) or "All 3 attempts failed" in str(
            result.error
        )

    @pytest.mark.asyncio
    async def test_with_timeout_success(self, action_context):
        """Test timeout logic with successful execution."""

        # Create a mock action that succeeds quickly
        class QuickAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Ok("Quick success")

        # Add timeout
        action_with_timeout = QuickAction().with_timeout(timeout_ms=1000)

        # Execute and verify
        result = await action_with_timeout.execute(action_context)

        assert result.is_ok()
        assert result.default_value(None) == "Quick success"

    @pytest.mark.asyncio
    async def test_with_timeout_timeout_occurs(self, action_context):
        """Test timeout logic when timeout occurs."""
        import asyncio

        # Create a mock action that takes too long
        class SlowAction(Action[str]):
            async def execute(self, context: ActionContext):
                await asyncio.sleep(0.1)  # Simulate slow operation
                return Ok("Slow success")

        # Add timeout that will trigger
        action_with_timeout = SlowAction().with_timeout(timeout_ms=10)

        # Execute and verify
        result = await action_with_timeout.execute(action_context)

        assert result.is_error()
        assert "timed out" in str(result.error).lower()

    @pytest.mark.asyncio
    async def test_pipe_operator(self, action_context):
        """Test the >> (pipe) operator for function composition."""

        # Create a mock action
        class TextAction(Action[str]):
            async def execute(self, context: ActionContext):
                return Ok("hello")

        # Use pipe operator to compose with a function
        def to_uppercase(s):
            return s.upper()

        piped_action = TextAction() >> to_uppercase

        # Execute and verify
        result = await piped_action.execute(action_context)

        assert result.is_ok()
        assert result.default_value(None) == "HELLO"

    @pytest.mark.asyncio
    async def test_pipe_operator_with_action(
        self, action_context, mock_browser_page, mock_element_handle
    ):
        """Test the >> operator for action sequencing."""
        # Setup mock behaviors - properly handle element selection
        mock_browser_page.query_selector.side_effect = lambda selector: Ok(
            mock_element_handle
        )
        mock_element_handle.click.return_value = Ok(None)
        mock_browser_page.fill.return_value = Ok(None)

        # Create a sequence of actions
        first_action = Click("#button")
        second_action = Fill("#input", "test")

        # Sequence the actions using pipe
        piped_action = first_action >> second_action

        # Execute and verify
        result = await piped_action.execute(action_context)

        assert result.is_ok()
        # The result should be from the second action
        mock_browser_page.fill.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_operator(
        self, action_context, mock_browser_page, mock_element_handle
    ):
        """Test the | (fallback) operator."""
        # Setup mock behaviors - first action fails, second succeeds
        first_call = True

        def query_selector_side_effect(selector):
            nonlocal first_call
            if first_call:
                first_call = False
                return Error(Exception("Element not found"))
            return Ok(mock_element_handle)

        mock_browser_page.query_selector.side_effect = query_selector_side_effect
        mock_element_handle.click.return_value = Ok(None)

        # Create actions with different selectors
        first_action = Click("#nonexistent")
        second_action = Click("#backup-button")

        # Use fallback operator
        fallback_action = first_action | second_action

        # Execute and verify
        result = await fallback_action.execute(action_context)

        assert result.is_ok()
        assert mock_browser_page.query_selector.call_count == 2

    @pytest.mark.asyncio
    async def test_parallel_operator(
        self,
        action_context,
        mock_browser_manager,
        mock_browser_context,
        mock_browser_page,
    ):
        """Test the & (parallel) operator."""
        # Setup mock behaviors for parallel execution
        mock_browser_manager.create_context.side_effect = [
            Ok(mock_browser_context),
            Ok(mock_browser_context),
        ]
        mock_browser_context.get_page.return_value = Ok(mock_browser_page)
        mock_browser_page.fill.return_value = Ok(None)

        # Create two actions
        first_action = Fill("#input1", "value1")
        second_action = Fill("#input2", "value2")

        # Use parallel operator
        parallel_action = first_action & second_action

        # Execute and verify
        result = await parallel_action.execute(action_context)

        if result.is_error():
            print(f"result: {result}, result error: {result.error}")

        value_tuple = result.default_value(None)
        assert value_tuple is not None
        assert len(value_tuple) == 2

        assert mock_browser_manager.create_context.call_count == 2
        assert mock_browser_context.get_page.call_count == 4
        assert mock_browser_manager.close_context.call_count == 2

    @pytest.mark.asyncio
    async def test_create_action_helper(self, action_context):
        """Test the create_action helper function."""

        # Create a custom action using the helper
        async def custom_logic(ctx):
            return Ok("Custom action result")

        custom_action = create_action(custom_logic)

        # Execute and verify
        result = await custom_action.execute(action_context)

        assert result.is_ok()
        assert result.default_value(None) == "Custom action result"

    @pytest.mark.asyncio
    async def test_executable_action(
        self, mock_browser_manager, mock_browser_context, mock_browser_page
    ):
        """Test calling an action directly with a browser manager."""
        # Setup mocks
        mock_browser_manager.create_context.return_value = Ok(mock_browser_context)
        mock_browser_context.get_page.return_value = Ok(mock_browser_page)
        mock_browser_page.fill.return_value = Ok(None)

        # Create an action
        action = Fill("#input", "test value")

        # Execute directly with browser manager
        result = await action(mock_browser_manager)

        assert result.is_ok()
        mock_browser_manager.create_context.assert_called_once()
        # Update to match actual behavior - get_page is called twice
        assert mock_browser_context.get_page.call_count == 2
        mock_browser_page.fill.assert_called_once()
        # Context should be closed when done
        mock_browser_manager.close_context.assert_called_once()


class TestSequence:
    @pytest.mark.asyncio
    async def test_sequence_all_success(self, action_context):
        """Test sequence with all successful actions."""

        # Create mock actions
        async def action1_func(ctx):
            return Ok("result1")

        async def action2_func(ctx):
            return Ok("result2")

        async def action3_func(ctx):
            return Ok("result3")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)
        action3 = create_action(action3_func)

        # Create sequence
        sequence_action = sequence(action1, action2, action3)

        # Execute
        result = await sequence_action.execute(action_context)

        # Verify
        assert result.is_ok()
        block = result.default_value(None)
        assert isinstance(block, Block)
        assert list(block) == [
            "result3",
            "result2",
            "result1",
        ]  # Results are collected in a Block

    @pytest.mark.asyncio
    async def test_sequence_one_fails(self, action_context):
        """Test sequence when one action fails."""

        # Create mock actions
        async def action1_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result1")

        async def action2_func(ctx):
            await asyncio.sleep(0.01)
            return Error(Exception("Action 2 failed"))

        async def action3_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result3")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)
        action3 = create_action(action3_func)

        # Create sequence
        sequence_action = sequence(action1, action2, action3)

        # Execute
        result = await sequence_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "Action 2 failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_sequence_empty_actions_error(self):
        """Test sequence with no actions raises ValueError."""
        with pytest.raises(ValueError):
            sequence()


class TestParallel:
    @pytest.mark.asyncio
    async def test_parallel_all_success(
        self,
        action_context,
        mock_browser_manager,
        mock_browser_context,
        mock_browser_page,
    ):
        """Test parallel with all successful actions."""
        # Setup mock behaviors for parallel execution
        mock_browser_manager.create_context.side_effect = [
            Ok(mock_browser_context),
            Ok(mock_browser_context),
            Ok(mock_browser_context),
        ]
        mock_browser_context.get_page.return_value = Ok(mock_browser_page)

        # Create mock actions
        async def action1_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result1")

        async def action2_func(ctx):
            await asyncio.sleep(0.02)
            return Ok("result2")

        async def action3_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result3")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)
        action3 = create_action(action3_func)

        # Create parallel action
        parallel_action = parallel(action1, action2, action3)

        # Execute
        result = await parallel_action.execute(action_context)

        # Verify
        assert result.is_ok()
        block = result.default_value(None)
        assert isinstance(block, Block)
        assert set(block) == {
            "result1",
            "result2",
            "result3",
        }  # Order is not guaranteed in parallel

        # Verify browser context creation and cleanup
        assert mock_browser_manager.create_context.call_count == 3
        assert mock_browser_manager.close_context.call_count == 3

    @pytest.mark.asyncio
    async def test_parallel_one_fails(
        self,
        action_context,
        mock_browser_manager,
        mock_browser_context,
        mock_browser_page,
    ):
        """Test parallel when one action fails."""
        # Setup mock behaviors for parallel execution
        mock_browser_manager.create_context.side_effect = [
            Ok(mock_browser_context),
            Ok(mock_browser_context),
            Ok(mock_browser_context),
        ]
        mock_browser_context.get_page.return_value = Ok(mock_browser_page)

        # Create mock actions
        async def action1_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result1")

        async def action2_func(ctx):
            await asyncio.sleep(0.01)
            return Error(Exception("Action 2 failed"))

        async def action3_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result3")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)
        action3 = create_action(action3_func)

        # Create parallel action
        parallel_action = parallel(action1, action2, action3)

        # Execute
        result = await parallel_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "Action 2 failed" in str(result.error)

        # Verify contexts are cleaned up even on failure
        assert mock_browser_manager.close_context.call_count == 3

    @pytest.mark.asyncio
    async def test_parallel_no_browser_manager(self, action_context):
        """Test parallel without a browser manager."""
        # Remove browser manager from context
        action_context.browser_manager = None

        async def action1_func(ctx):
            await asyncio.sleep(0.01)
            return Ok("result1")

        action1 = create_action(action1_func)
        parallel_action = parallel(action1)

        # Execute
        result = await parallel_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "Cannot execute parallel actions without a browser manager" in str(
            result.error
        )

    @pytest.mark.asyncio
    async def test_parallel_empty_actions_error(self):
        """Test parallel with no actions raises ValueError."""
        with pytest.raises(ValueError):
            parallel()


class TestPipe:
    @pytest.mark.asyncio
    async def test_pipe_action_to_callables(self, action_context):
        """Test pipe with an action followed by transformation callables."""

        # Create an action and transformations
        async def initial_action_func(ctx):
            await asyncio.sleep(0.01)
            return Ok(5)

        def double(val):
            async def double_func(ctx):
                await asyncio.sleep(0.01)
                return Ok(val * 2)

            return create_action(double_func)

        def add_ten(val):
            async def add_ten_func(ctx):
                await asyncio.sleep(0.01)
                return Ok(val + 10)

            return create_action(add_ten_func)

        initial_action = create_action(initial_action_func)

        # Create pipe
        pipe_action = pipe(initial_action, double, add_ten)

        # Execute
        result = await pipe_action.execute(action_context)

        # Verify - should be (5 * 2) + 10 = 20
        assert result.is_ok()
        assert result.default_value(None) == 20

    @pytest.mark.asyncio
    async def test_pipe_first_action_fails(self, action_context):
        """Test pipe when the first action fails."""

        # Create actions
        async def failing_action_func(ctx):
            return Error(Exception("First action failed"))

        async def next_action_func(val):
            return Ok(val * 2)

        failing_action = create_action(failing_action_func)

        def next_action(val):
            return create_action(next_action_func)

        # Create pipe
        pipe_action = pipe(failing_action, next_action)

        # Execute
        result = await pipe_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "First action failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_pipe_later_action_fails(self, action_context):
        """Test pipe when a later action fails."""

        # Create actions
        async def initial_action_func(ctx):
            return Ok(5)

        async def failing_action_func(val):
            return Error(Exception("Second action failed"))

        initial_action = create_action(initial_action_func)

        def failing_action(val):
            return create_action(failing_action_func)

        # Create pipe
        pipe_action = pipe(initial_action, failing_action)

        # Execute
        result = await pipe_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "Second action failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_pipe_first_callable_error(self, action_context):
        """Test pipe with a callable as first item should raise an error."""

        def not_an_action(val):
            async def not_an_action_func(ctx):
                return Ok(val * 2)

            return create_action(not_an_action_func)

        # Use pytest.raises to catch the expected error
        with pytest.raises(
            ValueError, match="First item in pipe must be an Action, not a callable"
        ):
            pipe_action = pipe(not_an_action)
            result = await pipe_action.execute(action_context)
            assert result.is_error()
            assert "First item in pipe must be an Action, not a callable" in str(
                result.error
            )

    @pytest.mark.asyncio
    async def test_pipe_empty_error(self):
        """Test pipe with no actions raises ValueError."""
        with pytest.raises(ValueError):
            pipe()


class TestFallback:
    @pytest.mark.asyncio
    async def test_fallback_first_succeeds(self, action_context):
        """Test fallback when the first action succeeds."""

        # Create actions
        async def action1_func(ctx):
            return Ok("action1 result")

        async def action2_func(ctx):
            return Ok("action2 result")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)

        # Create fallback
        fallback_action = fallback(action1, action2)

        # Execute
        result = await fallback_action.execute(action_context)

        # Verify - should return result from the first action
        assert result.is_ok()
        assert result.default_value(None) == "action1 result"

    @pytest.mark.asyncio
    async def test_fallback_first_fails_second_succeeds(self, action_context):
        """Test fallback when the first action fails but second succeeds."""

        # Create actions
        async def action1_func(ctx):
            return Error(Exception("Action 1 failed"))

        async def action2_func(ctx):
            return Ok("action2 result")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)

        # Create fallback
        fallback_action = fallback(action1, action2)

        # Execute
        result = await fallback_action.execute(action_context)

        # Verify - should return result from the second action
        assert result.is_ok()
        assert result.default_value(None) == "action2 result"

    @pytest.mark.asyncio
    async def test_fallback_all_fail(self, action_context):
        """Test fallback when all actions fail."""

        # Create actions
        async def action1_func(ctx):
            return Error(Exception("Action 1 failed"))

        async def action2_func(ctx):
            return Error(Exception("Action 2 failed"))

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)

        # Create fallback
        fallback_action = fallback(action1, action2)

        # Execute
        result = await fallback_action.execute(action_context)

        # Verify - should return last error
        assert result.is_error()
        assert "Action 2 failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_fallback_with_exception(self, action_context):
        """Test fallback when an action raises an exception."""

        # Create actions
        def raise_exception(ctx):
            raise Exception("Action raised exception")

        async def action2_func(ctx):
            return Ok("action2 result")

        action1 = create_action(raise_exception)
        action2 = create_action(action2_func)

        # Create fallback
        fallback_action = fallback(action1, action2)

        # Execute
        result = await fallback_action.execute(action_context)

        # Verify - should handle exception and try the next action
        assert result.is_ok()
        assert result.default_value(None) == "action2 result"

    @pytest.mark.asyncio
    async def test_fallback_empty_error(self):
        """Test fallback with no actions raises ValueError."""
        with pytest.raises(ValueError):
            fallback()


class TestCompose:
    @pytest.mark.asyncio
    async def test_compose_multiple_actions(self, action_context):
        """Test compose with multiple successful actions."""

        # Create actions
        async def action1_func(ctx):
            return Ok("action1 result")

        async def action2_func(ctx):
            return Ok("action2 result")

        async def action3_func(ctx):
            return Ok("action3 result")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)
        action3 = create_action(action3_func)

        # Create compose
        compose_action = compose(action1, action2, action3)

        # Execute
        result = await compose_action.execute(action_context)

        # Verify - should return only the last result
        assert result.is_ok()
        assert result.default_value(None) == "action3 result"

    @pytest.mark.asyncio
    async def test_compose_first_fails(self, action_context):
        """Test compose when first action fails."""

        # Create actions
        async def action1_func(ctx):
            return Error(Exception("Action 1 failed"))

        async def action2_func(ctx):
            return Ok("action2 result")

        action1 = create_action(action1_func)
        action2 = create_action(action2_func)

        # Create compose
        compose_action = compose(action1, action2)

        # Execute
        result = await compose_action.execute(action_context)

        # Verify - should return the error from the first action
        assert result.is_error()
        assert "Action 1 failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_compose_middle_fails(self, action_context):
        """Test compose when middle action fails."""

        # Create actions
        async def success1(ctx):
            return Ok("action1 result")

        async def fail2(ctx):
            return Error(Exception("Action 2 failed"))

        async def success3(ctx):
            return Ok("action3 result")

        action1 = create_action(success1)
        action2 = create_action(fail2)
        action3 = create_action(success3)

        # Create compose
        compose_action = compose(action1, action2, action3)

        # Execute
        result = await compose_action.execute(action_context)

        # Verify - should return the error from the failing action
        assert result.is_error()
        assert "Action 2 failed" in str(result.error)

    @pytest.mark.asyncio
    async def test_compose_single_action(self, action_context):
        """Test compose with a single action returns that action."""

        # Create action
        async def success(ctx):
            return Ok("single action result")

        action = create_action(success)

        # Create compose with single action
        compose_action = compose(action)

        # Should return the original action
        assert compose_action is action

    @pytest.mark.asyncio
    async def test_compose_empty_error(self):
        """Test compose with no actions raises ValueError."""
        with pytest.raises(ValueError):
            compose()

    @pytest.mark.asyncio
    async def test_compose_middle_fails_simple(self, action_context):
        """Simplified test to debug the issue."""

        # Create actions with async results
        async def success1(ctx):
            return Ok("action1 result")

        async def fail2(ctx):
            return Error(Exception("Action 2 failed"))

        async def success3(ctx):
            return Ok("action3 result")

        action1 = create_action(success1)
        action2 = create_action(fail2)
        action3 = create_action(success3)

        # Create compose
        compose_action = compose(action1, action2, action3)

        # Execute
        result = await compose_action.execute(action_context)

        # Verify
        assert result.is_error()
        assert "Action 2 failed" in str(result.error)
