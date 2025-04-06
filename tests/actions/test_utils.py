import pytest
from typing import Any, TypeVar, Awaitable, Union, cast
from expression import Result, Ok, Error, pipe
from unittest.mock import AsyncMock, MagicMock, patch

from silk.actions.base import Action, create_action, wrap_result
from silk.browsers.driver import BrowserDriver

T = TypeVar("T")


class TestActionUtils:
    @pytest.mark.asyncio
    async def test_create_action_with_function(self, mock_driver: BrowserDriver) -> None:
        # Test create_action with a synchronous function
        async def sync_function(driver: BrowserDriver) -> Result[str, Exception]:
            return Ok("sync result")
        
        # Create action from synchronous function
        action: Action[str] = create_action(sync_function)
        
        # Execute the action
        result = await action.execute(mock_driver)
        
        # The result should be wrapped in Ok
        assert result.is_ok()
        assert result.default_value(None) == "sync result"

    @pytest.mark.asyncio
    async def test_create_action_with_async_function(self, mock_driver: BrowserDriver) -> None:
        # Test create_action with an asynchronous function
        async def async_function(driver: BrowserDriver) -> Result[str, Exception]:
            return Ok("async result")
        
        # Create action from asynchronous function
        action: Action[str] = create_action(async_function)
        
        # Execute the action
        result = await action.execute(mock_driver)
        
        # The result should be wrapped in Ok
        assert result.is_ok()
        assert result.default_value(None) == "async result"

    @pytest.mark.asyncio
    async def test_create_action_with_function_that_raises(self, mock_driver: BrowserDriver) -> None:
        # Test create_action with a function that raises an exception
        async def error_function(driver: BrowserDriver) -> Result[str, Exception]:
            raise ValueError("Intentional error")
        
        # Create action from function that raises
        action: Action[str] = create_action(error_function)
        
        # Execute the action
        result = await action.execute(mock_driver)
        
        # The exception should be caught and wrapped in Error
        assert result.is_error()
        assert isinstance(result.error, ValueError)
        assert "Intentional error" in str(result.error)

    @pytest.mark.asyncio
    async def test_create_action_with_function_returning_result(self, mock_driver: BrowserDriver) -> None:
        # Test create_action with a function that already returns a Result
        async def result_function(driver: BrowserDriver) -> Result[str, Exception]:
            return Ok("already wrapped result")
        
        # Create action from function returning a Result
        action: Action[str] = create_action(result_function)
        
        # Execute the action
        result = await action.execute(mock_driver)
        
        # The Result should be preserved
        assert result.is_ok()
        assert result.default_value(None) == "already wrapped result"

    @pytest.mark.asyncio
    async def test_create_action_with_function_returning_error(self, mock_driver: BrowserDriver) -> None:
        # Test create_action with a function that returns an Error
        async def error_result_function(driver: BrowserDriver) -> Result[str, Exception]:
            return Error(ValueError("Known error"))
        
        # Create action from function returning an Error
        action: Action[str] = create_action(error_result_function)
        
        # Execute the action
        result = await action.execute(mock_driver)
        
        # The Error should be preserved
        assert result.is_error()
        assert isinstance(result.error, ValueError)
        assert "Known error" in str(result.error)

    def test_wrap_result_with_value(self) -> None:
        # Test wrap_result with a regular value
        value = "test value"
        result: Result[str, Exception] = wrap_result(value)
        
        # The value should be wrapped in Ok
        assert result.is_ok()
        assert result.default_value(None) == "test value"

    def test_wrap_result_with_result(self) -> None:
        # Test wrap_result with an already wrapped Ok value
        ok_result: Result[str, Exception] = Ok("already wrapped")
        result: Result[str, Exception] = wrap_result(ok_result)
        
        # The Result should be preserved
        assert result.is_ok()
        assert result.default_value(None) == "already wrapped"
        assert result is ok_result  # Should be the same object

    def test_wrap_result_with_error(self) -> None:
        # Test wrap_result with an Error value
        error_result: Result[str, Exception] = Error(ValueError("test error"))
        result: Result[str, Exception] = wrap_result(error_result)
        
        # The Error should be preserved
        assert result.is_error()
        assert isinstance(result.error, ValueError)
        assert "test error" in str(result.error)
        assert result is error_result  # Should be the same object

    def test_wrap_result_with_exception(self) -> None:
        # Test wrap_result with an exception
        exception = ValueError("test exception")
        
        # When wrapping an exception directly, it should be wrapped in Error
        result: Result[Any, Exception] = wrap_result(exception)
        
        assert result.is_error()
        assert result.error is exception  # Should be the same exception object 