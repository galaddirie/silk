import pytest
from typing import Callable, Any
from expression import Result, Ok, Error
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from silk.actions.base import Action
from silk.browsers.driver import BrowserDriver


class SimpleAction(Action[str]):
    """A simple action implementation for testing"""
    
    def __init__(self, return_value: str, should_fail: bool = False) -> None:
        self.return_value = return_value
        self.should_fail = should_fail
    
    async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
        if self.should_fail:
            return Error(Exception(f"Action failed"))
        return Ok(self.return_value)


class TestAction:
    @pytest.mark.asyncio
    async def test_action_execute(self, mock_driver: BrowserDriver) -> None:
        # Test successful action
        success_action = SimpleAction("success result")
        result = await success_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "success result"
        
        # Test failed action
        fail_action = SimpleAction("", should_fail=True)
        result = await fail_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Action failed" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_action_map(self, mock_driver: BrowserDriver) -> None:
        action = SimpleAction("original")
        mapped_action = action.map(lambda s: s.upper())
        
        result = await mapped_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "ORIGINAL"
        
        # Test mapping a failed action
        fail_action = SimpleAction("", should_fail=True)
        mapped_fail = fail_action.map(lambda s: s.upper())
        result = await mapped_fail.execute(mock_driver)
        
        assert result.is_error()
    
    @pytest.mark.asyncio
    async def test_action_and_then(self, mock_driver: BrowserDriver) -> None:
        first_action = SimpleAction("first result")
        
        def create_second_action(first_result: str) -> Action[str]:
            return SimpleAction(f"{first_result} -> second result")
        
        chained_action = first_action.and_then(create_second_action)
        
        result = await chained_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "first result -> second result"
        
        # Test chaining after a failed action
        fail_action = SimpleAction("", should_fail=True)
        chained_fail = fail_action.and_then(create_second_action)
        result = await chained_fail.execute(mock_driver)
        
        assert result.is_error()
    
    @pytest.mark.asyncio
    async def test_action_retry(self, mock_driver: BrowserDriver) -> None:
        # Action that fails on first attempt but succeeds on second
        attempts = 0
        
        class RetryTestAction(Action[str]):
            async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
                nonlocal attempts
                attempts += 1
                if attempts < 2:
                    return Error(Exception("Failed attempt"))
                return Ok("Success after retry")
        
        action = RetryTestAction()
        retry_action = action.retry(max_attempts=3, delay_ms=100)
        
        result = await retry_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "Success after retry"
        assert attempts == 2
        
        # Test retry with all attempts failing
        always_fail = SimpleAction("", should_fail=True)
        retry_fail = always_fail.retry(max_attempts=2, delay_ms=100)
        
        result = await retry_fail.execute(mock_driver)
        
        assert result.is_error()
    
    @pytest.mark.asyncio
    async def test_action_rshift_operator_with_function(self, mock_driver: BrowserDriver) -> None:
        action = SimpleAction("original")
        result_action = action >> (lambda s: s.upper())
        
        result = await result_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "ORIGINAL"
    
    @pytest.mark.asyncio
    async def test_action_rshift_operator_with_action(self, mock_driver: BrowserDriver) -> None:
        first_action = SimpleAction("first result")
        second_action = SimpleAction("second result")
        
        # first >> second should execute first, then second, ignoring first's result
        combined_action = first_action >> second_action
        
        result = await combined_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "second result"  # Should be second action's result
    
    @pytest.mark.asyncio
    async def test_action_or_operator(self, mock_driver: BrowserDriver) -> None:
        success_action = SimpleAction("success result")
        fallback_action = SimpleAction("fallback result")
        
        # Test fallback not needed
        combined = success_action | fallback_action
        result = await combined.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "success result"
        
        # Test fallback used
        fail_action = SimpleAction("", should_fail=True)
        combined = fail_action | fallback_action
        result = await combined.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "fallback result"
    
    @pytest.mark.asyncio
    async def test_action_and_operator(self, mock_driver: BrowserDriver) -> None:
        first_action = SimpleAction("first result")
        second_action = SimpleAction("second result")
        
        # first & second should execute both actions in parallel
        parallel_action = first_action & second_action
        
        result = await parallel_action.execute(mock_driver)
        
        assert result.is_ok()
        value = result.default_value(None)
        assert value is not None and len(value) == 2
    
    @pytest.mark.asyncio
    async def test_action_call(self, mock_driver: BrowserDriver) -> None:
        action = SimpleAction("result")
        
        # Test calling action directly
        result = await action(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "result" 