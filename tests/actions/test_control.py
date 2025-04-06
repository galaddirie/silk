import pytest
from expression import Result, Ok, Error
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from silk.actions.base import Action
from silk.actions.control import (
    branch,
    loop_until,
    retry_with_backoff,
    with_timeout,
    tap
)
from silk.browsers.driver import BrowserDriver

class SimpleTestAction(Action[str]):
    """A simple action implementation for testing"""
    
    def __init__(self, return_value: str, should_fail: bool = False):
        super().__init__()
        self.return_value = return_value
        self.should_fail = should_fail
        self.execute_count = 0
    
    async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
        self.execute_count += 1
        if self.should_fail:
            return Error(Exception(f"Action {self.return_value} failed"))
        return Ok(self.return_value)


class TestControlActions:
    @pytest.mark.asyncio
    async def test_branch_true_condition(self, mock_driver: AsyncMock) -> None:
        # Test branch with true condition
        condition_action = SimpleTestAction("true", should_fail=False)
        if_true_action = SimpleTestAction("true result", should_fail=False)
        if_false_action = SimpleTestAction("false result", should_fail=False)
        
        # Create a branch action that executes if_true_action when condition succeeds
        branch_action = branch(
            condition_action,
            if_true=if_true_action,
            if_false=if_false_action
        )
        
        result = await branch_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "true result"
        assert condition_action.execute_count == 1
        assert if_true_action.execute_count == 1
        assert if_false_action.execute_count == 0  # False branch should not execute

    @pytest.mark.asyncio
    async def test_branch_false_condition(self, mock_driver: AsyncMock) -> None:
        # Test branch with false condition (condition fails)
        condition_action = SimpleTestAction("false", should_fail=True)
        if_true_action = SimpleTestAction("true result", should_fail=False)
        if_false_action = SimpleTestAction("false result", should_fail=False)
        
        # Create a branch action that executes if_false_action when condition fails
        branch_action = branch(
            condition_action,
            if_true=if_true_action,
            if_false=if_false_action
        )
        
        result = await branch_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "false result"
        assert condition_action.execute_count == 1
        assert if_true_action.execute_count == 0  # True branch should not execute
        assert if_false_action.execute_count == 1

    @pytest.mark.asyncio
    async def test_branch_without_false_branch(self, mock_driver: AsyncMock) -> None:
        # Test branch without an if_false action
        condition_action = SimpleTestAction("false", should_fail=True)
        if_true_action = SimpleTestAction("true result", should_fail=False)
        
        # Create a branch action without if_false
        branch_action = branch(
            condition_action,
            if_true=if_true_action
        )
        
        result = await branch_action.execute(mock_driver)
        
        # Should return Ok(None) when condition fails and no if_false is provided
        assert result.is_ok()
        assert result.default_value("default") is None
        assert condition_action.execute_count == 1
        assert if_true_action.execute_count == 0

    @pytest.mark.asyncio
    async def test_loop_until_immediate_success(self, mock_driver: AsyncMock) -> None:
        # Test loop_until with immediate success
        condition_action = SimpleTestAction("true", should_fail=False)
        body_action = SimpleTestAction("body result", should_fail=False)
        
        # Create a loop_until action that should execute once
        loop_action = loop_until(
            condition=condition_action,
            body=body_action,
            max_iterations=5,
            delay_ms=100
        )
        
        result = await loop_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "body result"
        assert body_action.execute_count == 1  # Should execute once
        assert condition_action.execute_count == 1  # Should check once

    @pytest.mark.asyncio
    async def test_loop_until_eventual_success(self, mock_driver: AsyncMock) -> None:
        # Test loop_until with eventual success after multiple iterations
        execute_counts = {"condition": 0}
        
        class EventualSuccessCondition(Action[str]):
            async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
                execute_counts["condition"] += 1
                # Succeed on the third attempt
                if execute_counts["condition"] >= 3:
                    return Ok("condition met")
                return Error(Exception("Condition not met yet"))
        
        condition_action = EventualSuccessCondition()
        body_action = SimpleTestAction("body result", should_fail=False)
        
        # Create a loop_until action
        loop_action = loop_until(
            condition=condition_action,
            body=body_action,
            max_iterations=5,
            delay_ms=10  # Use small delay for faster test
        )
        
        result = await loop_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "body result"
        assert body_action.execute_count == 3  # Should execute three times
        assert execute_counts["condition"] == 3  # Should check condition three times

    @pytest.mark.asyncio
    async def test_loop_until_max_iterations_reached(self, mock_driver: AsyncMock) -> None:
        # Test loop_until when max iterations is reached without success
        condition_action = SimpleTestAction("false", should_fail=True)
        body_action = SimpleTestAction("body result", should_fail=False)
        
        # Create a loop_until action with max_iterations=3
        loop_action = loop_until(
            condition=condition_action,
            body=body_action,
            max_iterations=3,
            delay_ms=10  # Use small delay for faster test
        )
        
        result = await loop_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Maximum iterations (3) reached" in str(result.error)
        assert body_action.execute_count == 3  # Should execute three times
        assert condition_action.execute_count == 3  # Should check three times

    @pytest.mark.asyncio
    async def test_retry_with_backoff_immediate_success(self, mock_driver: AsyncMock) -> None:
        # Test retry_with_backoff with immediate success
        action = SimpleTestAction("success", should_fail=False)
        
        retry_action = retry_with_backoff(
            action,
            max_attempts=3,
            initial_delay_ms=100,
            backoff_factor=2
        )
        
        result = await retry_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "success"
        assert action.execute_count == 1  # Should execute once

    @pytest.mark.asyncio
    async def test_retry_with_backoff_eventual_success(self, mock_driver: AsyncMock) -> None:
        # Test retry_with_backoff with eventual success
        execute_counts = {"action": 0}
        
        class EventualSuccessAction(Action[str]):
            async def execute(self, driver:BrowserDriver) -> Result[str, Exception]:
                execute_counts["action"] += 1
                # Succeed on the third attempt
                if execute_counts["action"] >= 3:
                    return Ok("eventual success")
                return Error(Exception("Not yet successful"))
        
        action = EventualSuccessAction()
        
        retry_action = retry_with_backoff(
            action,
            max_attempts=5,
            initial_delay_ms=10,  # Small delay for tests
            backoff_factor=1.5
        )
        
        result = await retry_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "eventual success"
        assert execute_counts["action"] == 3  # Should execute three times

    @pytest.mark.asyncio
    async def test_retry_with_backoff_all_attempts_fail(self, mock_driver: AsyncMock) -> None:
        # Test retry_with_backoff when all attempts fail
        action = SimpleTestAction("action", should_fail=True)
        
        retry_action = retry_with_backoff(
            action,
            max_attempts=3,
            initial_delay_ms=10,  # Small delay for tests
            backoff_factor=2
        )
        
        result = await retry_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Action action failed" in str(result.error)
        assert action.execute_count == 3  # Should have attempted 3 times

    @pytest.mark.asyncio
    async def test_with_timeout_success_within_timeout(self, mock_driver: AsyncMock) -> None:
        # Test with_timeout when action completes within timeout
        action = SimpleTestAction("quick result", should_fail=False)
        
        timeout_action = with_timeout(
            action,
            timeout_ms=1000  # 1 second timeout
        )
        
        result = await timeout_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "quick result"
        assert action.execute_count == 1

    @pytest.mark.asyncio
    async def test_with_timeout_exceeds_timeout(self, mock_driver: AsyncMock) -> None:
        # Test with_timeout when action exceeds timeout
        class SlowAction(Action[str]):
            async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
                await asyncio.sleep(0.2)  # Sleep for 200ms
                return Ok("slow result")
        
        action = SlowAction()
        
        timeout_action = with_timeout(
            action,
            timeout_ms=50  # 50ms timeout
        )
        
        result = await timeout_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Timeout" in str(result.error)

    @pytest.mark.asyncio
    async def test_tap_success(self, mock_driver: AsyncMock) -> None:
        # Test tap with successful action
        action = SimpleTestAction( "main result", should_fail=False)
        side_effect_action = SimpleTestAction("side effect", should_fail=False)
        
        tap_action = tap(
            action,
            side_effect=side_effect_action
        )
        
        result = await tap_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "main result"  # Should return the main action's result
        assert action.execute_count == 1
        assert side_effect_action.execute_count == 1

    @pytest.mark.asyncio
    async def test_tap_main_action_failure(self, mock_driver: AsyncMock) -> None:
        # Test tap when the main action fails
        action = SimpleTestAction( "", should_fail=True)
        side_effect_action = SimpleTestAction("side effect", should_fail=False)
        
        tap_action = tap(
            action,
            side_effect=side_effect_action
        )
        
        result = await tap_action.execute(mock_driver)
        
        assert result.is_error()
        assert "main_action failed" in str(result.error)
        assert action.execute_count == 1
        assert side_effect_action.execute_count == 0  # Side effect should not execute when main fails

    @pytest.mark.asyncio
    async def test_tap_side_effect_failure(self, mock_driver: AsyncMock) -> None:
        # Test tap when the side effect action fails
        action = SimpleTestAction("main result", should_fail=False)
        side_effect_action = SimpleTestAction("side effect", should_fail=True)
        
        tap_action = tap(
            action,
            side_effect=side_effect_action
        )
        
        result = await tap_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "main result"  # Should return the main action's result even if side effect fails
        assert action.execute_count == 1
        assert side_effect_action.execute_count == 1  # Side effect should execute
        # The error from the side effect is ignored 