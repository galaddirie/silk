from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Awaitable,
    Union,
    overload,
    cast,
    ParamSpec,
)
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from expression import pipe, curry, compose
from expression.core import Result, Some, Nothing, Error, Ok
from expression.collections import Block

from functools import reduce, wraps
import asyncio
from dataclasses import dataclass
import operator
import inspect

from silk.browser.driver import BrowserDriver
from silk.selectors.selector import Selector, SelectorGroup

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")

P = ParamSpec("P")  # Represents function parameters


class Action(Generic[T]):
    """Base class for all actions that can be performed in a browser"""

    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        # Use Option to handle the optional description
        self.description_option = (
            Some(description) if description is not None else Nothing
        )
        self.description = self.description_option.default_value(
            ""
        )  # Default to empty string if None

    @abstractmethod
    async def execute(self, driver: BrowserDriver) -> Result[T, Exception]:
        """
        Execute the action using the given browser driver

        Args:
            driver: Browser driver to execute the action with

        Returns:
            Result containing either the action result or an exception
        """
        pass

    def map(self, f: Callable[[T], S]) -> "Action[S]":
        """
        Create a new action that maps the result of this action

        Args:
            f: Function to transform the result

        Returns:
            A new Action with transformed result
        """
        original_action = self

        class MappedAction(Action[S]):
            def __init__(self) -> None:
                super().__init__(
                    name=f"map({original_action.name})",
                    description=f"Apply function to result of {original_action.name}",
                )

            async def execute(self, driver: BrowserDriver) -> Result[S, Exception]:
                result = await original_action.execute(driver)
                try:
                    return result.map(f)
                except Exception as e:
                    return Error(e)

        return MappedAction()

    def and_then(self, f: Callable[[T], "Action[S]"]) -> "Action[S]":
        """
        Chain an action after this one, using the result of this action

        Args:
            f: Function that takes the result of this action and returns a new action

        Returns:
            A new Action that chains the two actions
        """
        original_action = self

        class ChainedAction(Action[S]):
            def __init__(self) -> None:
                super().__init__(
                    name=f"{original_action.name} >>> and_then",
                    description=f"Chain action after {original_action.name}",
                )

            async def execute(self, driver: BrowserDriver) -> Result[S, Exception]:
                try:
                    # First execute the original action
                    result = await original_action.execute(driver)
                    
                    # If we have an error, return it directly
                    if result.is_error():
                        return cast(Result[S, Exception], result)
                    
                    # Get the next action using the result value
                    value = result.default_value(None)
                    if value is None:
                        return Error(Exception("No value to chain to"))
                    next_action = f(value)
                    
                    # Execute the next action and return its result
                    return await next_action.execute(driver)
                except Exception as e:
                    return Error(e)

        return ChainedAction()

    def retry(self, max_attempts: int = 3, delay_ms: int = 1000) -> "Action[T]":
        """
        Create a new action that retries this action multiple times until it succeeds

        Args:
            max_attempts: Maximum number of retry attempts
            delay_ms: Delay between retries in milliseconds

        Returns:
            A new Action with retry logic
        """
        original_action = self

        class RetryAction(Action[T]):
            def __init__(self) -> None:
                super().__init__(
                    name=f"retry({original_action.name}, {max_attempts}, {delay_ms})",
                    description=f"Retry {original_action.name} up to {max_attempts} times",
                )

            async def execute(self, driver: BrowserDriver) -> Result[T, Exception]:
                last_error = None

                for attempt in range(max_attempts):
                    try:
                        result = await original_action.execute(driver)
                        if result.is_ok():
                            return result
                        # Store the error for potential retry
                        last_error = result.error
                    except Exception as e:
                        last_error = e

                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay_ms / 1000)

                return Error(
                    last_error or Exception(f"All {max_attempts} attempts failed")
                )

        return RetryAction()

    def __rshift__(
        self, other: Union[Callable[[T], S], "Action[Any]"]
    ) -> "Action[Any]":
        """
        Overload the >> operator for pipe-like sequencing

        a >> b is equivalent to:
        - If b is a function: a.map(b)
        - If b is an Action: a.and_then(lambda _: b)
        """
        if isinstance(other, Action):
            # Sequence actions: a >> b means "do a, then do b (ignoring a's result)"
            return self.and_then(lambda _: other)
        else:
            # Apply function to result: a >> f means "do a, then apply f to result"
            return self.map(other)

    def __or__(self, other: "Action[S]") -> "Action[Union[T, S]]":
        """
        Overload the | operator for fallback behavior

        a | b means "try action a, if it fails, try action b"
        """
        first_action = self
        second_action = other

        class FallbackAction(Action[Union[T, S]]):
            def __init__(self) -> None:
                super().__init__(
                    name=f"({first_action.name} | {second_action.name})",
                    description=f"Try {first_action.name}, fall back to {second_action.name}",
                )

            async def execute(
                self, driver: BrowserDriver
            ) -> Result[Union[T, S], Exception]:
                try:
                    result = await first_action.execute(driver)
                    if result.is_ok():
                        return result
                except Exception:
                    pass

                # First action failed, try the second
                return await second_action.execute(driver)

        return FallbackAction()

    def __and__(self, other: "Action[S]") -> "Action[tuple[T, S]]":
        """
        Overload the & operator for parallel execution

        a & b means "execute actions a and b in parallel and return both results"
        """
        from silk.actions.composition import parallel

        return cast(
            Action[tuple[T, S]], 
            parallel(self, other).map(lambda results: (results[0], results[1]))
        )

    def __call__(self, driver: BrowserDriver) -> Awaitable[Result[T, Exception]]:
        """
        Make Action instances callable directly with a driver

        This allows using actions like: result = await action(driver)
        """
        return self.execute(driver)


# Factory function for creating actions from pure functions
def create_action(
    name: str,
    execute_fn: Callable[[BrowserDriver], Awaitable[Result[T, Exception]]],
    description: Optional[str] = None,
) -> Action[T]:
    """
    Create an action from a function

    Args:
        name: Name of the action
        execute_fn: Function that takes a driver and returns a Result
        description: Optional description

    Returns:
        An Action that wraps the function
    """

    class FunctionalAction(Action[T]):
        def __init__(self) -> None:
            super().__init__(name=name, description=description)

        async def execute(self, driver: BrowserDriver) -> Result[T, Exception]:
            try:
                return await execute_fn(driver)
            except Exception as e:
                return Error(e)

    return FunctionalAction()
