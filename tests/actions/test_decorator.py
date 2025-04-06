import pytest
from typing import Any, Dict
from expression import Result, Ok, Error
from unittest.mock import AsyncMock, MagicMock, patch

from silk.actions.base import Action
from silk.actions.decorators import action
from silk.browsers.driver import BrowserDriver


class TestActionDecorator:
    @pytest.mark.asyncio
    async def test_action_decorator_success(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a successful function
        @action()
        async def successful_action(driver: BrowserDriver) -> str:
            return "success result"
        
        # The decorator should convert the function into an Action
        assert isinstance(successful_action(), Action)
        
        # Execute the action
        result = await successful_action().execute(mock_driver)
        
        # The function result should be wrapped in an Ok
        assert result.is_ok()
        assert result.default_value(None) == "success result"

    @pytest.mark.asyncio
    async def test_action_decorator_with_exception(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a function that raises an exception
        @action()
        async def failing_action(driver: BrowserDriver) -> str:
            raise ValueError("Something went wrong")
        
        # Execute the action
        result = await failing_action().execute(mock_driver)
        
        # The exception should be caught and wrapped in an Error
        assert result.is_error()
        assert isinstance(result.error, ValueError)
        assert "Something went wrong" in str(result.error)

    @pytest.mark.asyncio
    async def test_action_decorator_with_result_type(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a function that already returns a Result
        @action()
        async def result_action(driver: BrowserDriver) -> Result[str, Exception]:
            return Ok("already wrapped result")
        
        # Execute the action
        result = await result_action().execute(mock_driver)
        
        # The Result should be preserved
        assert result.is_ok()
        assert result.default_value(None) == "already wrapped result"

    @pytest.mark.asyncio
    async def test_action_decorator_with_error_result(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a function that returns an Error
        @action()
        async def error_result_action(driver: BrowserDriver) -> Result[str, Exception]:
            return Error(ValueError("Known error"))
        
        # Execute the action
        result = await error_result_action().execute(mock_driver)
        
        # The Error should be preserved
        assert result.is_error()
        assert isinstance(result.error, ValueError)
        assert "Known error" in str(result.error)

    @pytest.mark.asyncio
    async def test_action_decorator_with_arguments(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a function that takes additional arguments
        @action()
        async def parameterized_action(driver: BrowserDriver, param1: str, param2: str) -> str:
            return f"param1={param1}, param2={param2}"
        
        # Create an action with arguments
        bound_action = parameterized_action("value1", "value2")
        
        # The arguments should be bound to the action
        assert isinstance(bound_action, Action)
        
        # Execute the action
        result = await bound_action.execute(mock_driver)
        
        # The result should include the bound parameters
        assert result.is_ok()
        assert result.default_value(None) == "param1=value1, param2=value2"

    @pytest.mark.asyncio
    async def test_action_decorator_with_kwargs(self, mock_driver: BrowserDriver) -> None:
        # Test the @action decorator with a function that takes keyword arguments
        @action()
        async def kwargs_action(driver: BrowserDriver, **kwargs: str) -> Dict[str, str]:
            return kwargs
        
        # Create an action with keyword arguments
        bound_action = kwargs_action(key1="value1", key2="value2")
        
        # Execute the action
        result = await bound_action.execute(mock_driver)
        
        # The result should include the keyword arguments
        assert result.is_ok()
        expected = {"key1": "value1", "key2": "value2"}
        assert result.default_value(None) == expected

    @pytest.mark.asyncio
    async def test_action_decorator_maintains_function_metadata(self) -> None:
        # Test that the @action decorator maintains function metadata like docstrings
        @action()
        async def documented_action(driver: BrowserDriver) -> str:
            """This is a test docstring for the action."""
            return "result"
        
        # Check that the docstring is maintained
        assert documented_action.__doc__ == "This is a test docstring for the action."

    @pytest.mark.asyncio  
    async def test_action_decorator_default_name(self, mock_driver: BrowserDriver) -> None:
        # Test that the @action decorator uses the function name if no name is provided
        @action()
        async def unnamed_action(driver: BrowserDriver) -> str:
            return "result from unnamed action"
        
        # Execute the action
        result = await unnamed_action().execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "result from unnamed action" 