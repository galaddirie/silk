import pytest
from typing import Any, Callable, List, Dict, TypeVar
from expression import Result, Ok, Error
from expression.collections import Block
from unittest.mock import AsyncMock, MagicMock, patch

from silk.actions.base import Action, create_action
from silk.browsers.driver import BrowserDriver
from silk.actions.composition import (
    parallel,
    pipe,
    compose,
    sequence,
    fallback
)

T = TypeVar('T')


class SimpleTestAction(Action[str]):
    """A simple action implementation for testing"""
    
    def __init__(self, return_value: str, should_fail: bool = False) -> None:
        self.return_value = return_value
        self.should_fail = should_fail
        self.execute_count = 0
    
    async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
        self.execute_count += 1
        if self.should_fail:
            return Error(Exception(f"Action failed"))
        return Ok(self.return_value)


class TestCompositionActions:
    @pytest.mark.asyncio
    async def test_parallel_all_succeed(self, mock_driver: BrowserDriver) -> None:
        # Test parallel execution with all actions succeeding
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=False)
        action3 = SimpleTestAction("result3", should_fail=False)
        
        parallel_action = parallel(action1, action2, action3)
        
        result = await parallel_action.execute(mock_driver)
        
        assert result.is_ok()
        results_block = result.default_value(None)
        assert isinstance(results_block, Block)
        assert len(results_block) == 3

        
        # Each action should have executed once
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 1

    @pytest.mark.asyncio
    async def test_parallel_some_fail(self, mock_driver: BrowserDriver) -> None:
        # Test parallel execution with some actions failing
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=True)  # This one fails
        action3 = SimpleTestAction("result3", should_fail=False)
        
        parallel_action = parallel(action1, action2, action3)
        
        result = await parallel_action.execute(mock_driver)
        
        # The overall result should be an Error
        assert result.is_error()
        assert "Action failed" in str(result.error)
        
        # All actions should have executed even though one failed
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 1

    @pytest.mark.asyncio
    async def test_pipe_all_succeed(self, mock_driver: BrowserDriver) -> None:
        # Test pipe with all actions succeeding
        steps: List[str] = []
        
        class StepAction(Action[str]):
            def __init__(self, transform_fn: Callable[[Any], str]) -> None:
                self.transform_fn = transform_fn
                self.input_value: Any = None
            
            async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
                steps.append("step")
                return Ok(self.transform_fn(self.input_value))
        
        # For testing, let's create simpler actions
        action1 = SimpleTestAction("step1_output", should_fail=False)
        
        # Create a function that takes the result of action1 and returns a new action
        def step2_action(prev_result: str) -> Action[str]:
            return SimpleTestAction(f"{prev_result}_processed_by_step2", should_fail=False)
            
        # Create a function that takes the result of step2 and returns a new action
        def step3_action(prev_result: str) -> Action[str]:
            return SimpleTestAction(f"{prev_result}_and_step3", should_fail=False)
        
        # Create a pipe using our actions
        from expression import curry
        
        # Create wrapper functions that return Actions
        @curry(1)
        def make_step2(step_fn: Callable[[str], Action[str]], value: str) -> Action[str]:
            return step_fn(value)
            
        @curry(1)
        def make_step3(step_fn: Callable[[str], Action[str]], value: str) -> Action[str]:
            return step_fn(value)
            
        # Now pipe the actions together
        pipe_action = pipe(
            action1,
            make_step2(step2_action),
            make_step3(step3_action)
        )
        
        result = await pipe_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == "step1_output_processed_by_step2_and_step3"

    @pytest.mark.asyncio
    async def test_pipe_with_failure(self, mock_driver: BrowserDriver) -> None:
        # Test pipe with a failing action in the middle
        steps: List[str] = []
        
        def create_step1(_input_value: str) -> Action[str]:
            return SimpleTestAction("step1_output", should_fail=False)
            
        def create_step2(step1_output: str) -> Action[str]:
            steps.append("create_step2 called with " + step1_output)
            return SimpleTestAction("", should_fail=True)  # This one fails
            
        def create_step3(step2_output: str) -> Action[str]:
            steps.append("create_step3 should not be called")
            return SimpleTestAction("step3_output", should_fail=False)
        
        # Create a pipe starting with an Action, not a string
        first_action = SimpleTestAction("initial_output", should_fail=False)
        
        from expression import curry
        
        # Create wrapper functions that return Actions
        @curry(1)
        def make_step2(step_fn: Callable[[str], Action[str]], value: str) -> Action[str]:
            return step_fn(value)
            
        @curry(1)
        def make_step3(step_fn: Callable[[str], Action[str]], value: str) -> Action[str]:
            return step_fn(value)
            
        # Now pipe the actions together
        pipe_action = pipe(
            first_action,
            make_step2(create_step2),
            make_step3(create_step3)
        )
        
        result = await pipe_action.execute(mock_driver)
        
        # The overall result should be an Error from step2
        assert result.is_error()
        assert "Action failed" in str(result.error)
        
        # Step3 should not have been created or executed
        assert "create_step3 should not be called" not in steps
        assert "create_step2 called with initial_output" in steps

    @pytest.mark.asyncio
    async def test_compose_all_succeed(self, mock_driver: BrowserDriver) -> None:
        # Test compose with all actions succeeding
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=False)
        action3 = SimpleTestAction("result3", should_fail=False)
        
        compose_action = compose(action1, action2, action3)
        
        result = await compose_action.execute(mock_driver)
        
        assert result.is_ok()
        # Compose should return the result of the last action
        assert result.default_value(None) == "result3"
        
        # Each action should have executed once in sequence
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 1

    @pytest.mark.asyncio
    async def test_compose_with_failure(self, mock_driver: BrowserDriver) -> None:
        # Test compose with a failing action in the middle
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=True)  # This one fails
        action3 = SimpleTestAction("result3", should_fail=False)
        
        compose_action = compose(action1, action2, action3)
        
        result = await compose_action.execute(mock_driver)
        
        # The overall result should be an Error from action2
        assert result.is_error()
        assert "Action failed" in str(result.error)
        
        # Action1 and action2 should have executed, but not action3
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 0

    @pytest.mark.asyncio
    async def test_sequence_all_succeed(self, mock_driver: BrowserDriver) -> None:
        # Test sequence with all actions succeeding
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=False)
        action3 = SimpleTestAction("result3", should_fail=False)
        
        sequence_action = sequence(action1, action2, action3)
        
        result = await sequence_action.execute(mock_driver)
        
        assert result.is_ok()
        # Sequence returns a Block of all results
        results_block = result.default_value(None)
        assert isinstance(results_block, Block)
        assert len(results_block) == 3
        
        # Each action should have executed once in sequence
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 1

    @pytest.mark.asyncio
    async def test_sequence_with_failure(self, mock_driver: BrowserDriver) -> None:
        # Test sequence with a failing action in the middle
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=True)  # This one fails
        action3 = SimpleTestAction("result3", should_fail=False)
        
        sequence_action = sequence(action1, action2, action3)
        
        result = await sequence_action.execute(mock_driver)
        
        # The overall result should be an Error from action2
        assert result.is_error()
        assert "Action failed" in str(result.error)
        
        # Action1 and action2 should have executed, but not action3
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 0

    @pytest.mark.asyncio
    async def test_fallback_first_succeeds(self, mock_driver: BrowserDriver) -> None:
        # Test fallback when the first action succeeds
        action1 = SimpleTestAction("result1", should_fail=False)
        action2 = SimpleTestAction("result2", should_fail=False)
        action3 = SimpleTestAction("result3", should_fail=False)
        
        fallback_action = fallback(action1, action2, action3)
        
        result = await fallback_action.execute(mock_driver)
        
        assert result.is_ok()
        # Fallback returns the result of the first successful action
        assert result.default_value(None) == "result1"
        
        # Only action1 should have executed
        assert action1.execute_count == 1
        assert action2.execute_count == 0
        assert action3.execute_count == 0

    @pytest.mark.asyncio
    async def test_fallback_first_fails(self, mock_driver: BrowserDriver) -> None:
        # Test fallback when the first action fails
        action1 = SimpleTestAction("result1", should_fail=True)
        action2 = SimpleTestAction("result2", should_fail=False)
        action3 = SimpleTestAction("result3", should_fail=False)
        
        fallback_action = fallback(action1, action2, action3)
        
        result = await fallback_action.execute(mock_driver)
        
        assert result.is_ok()
        # Fallback returns the result of the first successful action (action2)
        assert result.default_value(None) == "result2"
        
        # Action1 and action2 should have executed
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 0

    @pytest.mark.asyncio
    async def test_fallback_all_fail(self, mock_driver: BrowserDriver) -> None:
        # Test fallback when all actions fail
        action1 = SimpleTestAction("result1", should_fail=True)
        action2 = SimpleTestAction("result2", should_fail=True)
        action3 = SimpleTestAction("result3", should_fail=True)
        
        fallback_action = fallback(action1, action2, action3)
        
        result = await fallback_action.execute(mock_driver)
        
        # The overall result should be an Error from the last action
        assert result.is_error()
        assert "Action failed" in str(result.error)
        
        # All actions should have executed
        assert action1.execute_count == 1
        assert action2.execute_count == 1
        assert action3.execute_count == 1 