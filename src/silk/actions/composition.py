import asyncio
from typing import Any, Callable, TypeVar, Union, Optional

from expression.collections import Block
from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.models.browser import ActionContext

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")


def sequence(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Combines multiple actions into a single action that executes them in sequence.

    Unlike 'compose', this function collects and returns ALL results as a Block.

    Example:
    ```python
        result = await sequence(action1, action2, action3).execute(context)
        # result is Ok(Block[result1, result2, result3])
    ```

    Args:
        *actions: Actions to combine

    Returns:
        A new Action that executes all actions in sequence and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a sequence with no actions")

    class SequenceAction(Action[Block[Any]]):
        async def execute(
            self, context: ActionContext
        ) -> Result[Block[Any], Exception]:
            results = Block.empty()

            for action in action_list:
                try:
                    result = await action.execute(context)

                    if result.is_error():
                        return Error(result.error)

                    value = result.default_value(None)
                    if value is not None:
                        results = results.cons(value)
                except Exception as e:
                    return Error(e)

            return Ok(results.sort(reverse=True))

    return SequenceAction()


def pipe(*steps: Union[Action[Any], Callable[[Any], Action[Any]]]) -> Action[Any]:
    """
    Create a pipeline of actions where each step can be either an Action or
    a function that takes the previous result and returns an Action.

    This is the most flexible composition function:
    - For simple cases, use compose() or the >> operator
    - For complex cases where you need to inspect values or decide which action to run next,
      use pipe() with lambda functions

    Example:
    ```python
        result = await pipe(
            Query(".item"),                      # Returns an element
            lambda el: Click(el) if el else Navigate("/fallback"),  # Conditional logic
            ExtractText("#result")               # Extract result text
        ).execute(context)
    ```

    Args:
        *steps: Steps in the pipeline. Can be Action objects or callables
               that take a value and return an Action.

    Returns:
        A new Action that executes the steps in a pipeline
    """
    steps_list = list(steps)
    if not steps_list:
        raise ValueError("Cannot create a pipeline with no steps")
    if len(steps_list) == 1:
        first_step = steps_list[0]
        if callable(first_step) and not isinstance(first_step, Action):
            raise ValueError("First item in pipe must be an Action, not a callable")
        return first_step if isinstance(first_step, Action) else first_step(None)

    class PipelineAction(Action[Any]):
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                # Get the first action
                first_step = steps_list[0]
                if callable(first_step) and not isinstance(first_step, Action):
                    return Error(
                        Exception(
                            "First item in pipe must be an Action, not a callable"
                        )
                    )

                first_action = (
                    first_step if isinstance(first_step, Action) else first_step(None)
                )
                result = await first_action.execute(context)

                if result.is_error():
                    return result

                # Process each step in the pipeline
                value = result.default_value(None)

                for step in steps_list[1:]:
                    try:
                        # Create the next action from the step
                        if callable(step) and not isinstance(step, Action):
                            # If it's a callable, call it with the value from the previous step
                            next_action = step(value)
                        else:
                            # If it's an Action, adapt it to use the value if possible
                            next_action = (
                                step.with_input(value)
                                if hasattr(step, "with_input")
                                else step
                            )

                        if not isinstance(next_action, Action):
                            return Error(
                                Exception(
                                    f"Expected an Action but got {type(next_action)}: {next_action}"
                                )
                            )

                        # Execute the action
                        result = await next_action.execute(context)
                        if result.is_error():
                            return result

                        # Get the value for the next step
                        value = result.default_value(None)
                    except Exception as e:
                        return Error(e)

                # Return the final result
                return Ok(value)
            except Exception as e:
                return Error(e)

    return PipelineAction()


def parallel(*actions: Action[Any]) -> Action[Block[Any]]:
    """
    Execute multiple actions in parallel and collect their results into a Block.

    If any action fails, the whole operation fails with that error.

    Example:
    ```python
        result = await parallel(action1, action2, action3).execute(context)
        # result is Ok(Block[result1, result2, result3])
    ```

    Args:
        *actions: Actions to execute in parallel

    Returns:
        A new Action that executes all actions in parallel and returns a Block of their results
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a parallel execution with no actions")

    class ParallelAction(Action[Block[Any]]):
        async def execute(
            self, context: ActionContext
        ) -> Result[Block[Any], Exception]:
            if not context.browser_manager:
                return Error(
                    Exception(
                        "Cannot execute parallel actions without a browser manager"
                    )
                )

            try:
                tasks = []
                context_ids = []

                for action in action_list:
                    context_result = await context.browser_manager.create_context()
                    if context_result.is_error():
                        return Error(
                            Exception(
                                f"Failed to create context for parallel execution: {context_result.error}"
                            )
                        )

                    browser_context = context_result.default_value(None)
                    if browser_context is None:
                        return Error(
                            Exception(
                                "Failed to create browser context for parallel execution"
                            )
                        )

                    context_ids.append(browser_context.id)

                    page_result = browser_context.get_page()
                    if page_result.is_error():
                        return Error(
                            Exception(
                                f"Failed to get page for parallel execution: {page_result.error}"
                            )
                        )

                    page = page_result.default_value(None)
                    if page is None:
                        return Error(
                            Exception("Failed to get page for parallel execution")
                        )

                    action_context = ActionContext(
                        browser_manager=context.browser_manager,
                        context_id=browser_context.id,
                        page_id=page.id,
                        metadata={**context.metadata, "parallel_execution": True},
                    )

                    task = action.execute(action_context)
                    tasks.append(task)

                try:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    results_block = Block.of_seq(results)

                    for result in results_block:
                        if isinstance(result, Exception):
                            return Error(result)
                        if isinstance(result, Result) and result.is_error():
                            return Error(result.error)

                    values = Block.empty()
                    for result in results_block:
                        if isinstance(result, Result):
                            value = result.default_value(None)
                            if value is not None:
                                values = values.cons(value)
                        else:
                            values = values.cons(result)

                    return Ok(values.sort(reverse=True))
                finally:
                    for context_id in context_ids:
                        await context.browser_manager.close_context(context_id)
            except Exception as e:
                return Error(e)

    return ParallelAction()


def fallback(*actions: Action[T]) -> Action[T]:
    """
    Try actions in sequence until one succeeds.

    This is equivalent to the '|' operator between Actions.

    Example:
    ```python
        result = await fallback(
            action_might_fail,
            backup_action
        ).execute(context)
        # Returns result of first action that succeeds
    ```

    Args:
        *actions: Actions to try in order

    Returns:
        A new Action that tries each action until one succeeds
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot create a fallback with no actions")
    if len(action_list) == 1:
        return action_list[0]

    class FallbackAction(Action[T]):
        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            last_error = None

            for index, action in enumerate(action_list):
                try:
                    fallback_context = context.derive(
                        metadata={
                            "fallback_index": index,
                            "fallback_total": len(action_list),
                        }
                    )

                    result = await action.execute(fallback_context)
                    if result.is_ok():
                        return result

                    last_error = result.error
                except Exception as e:
                    last_error = e

            return Error(last_error or Exception("All fallback actions failed"))

    return FallbackAction()


def compose(*actions: Action[Any]) -> Action[Any]:
    """
    Compose multiple actions into a single action that executes them in sequence.

    Unlike 'sequence', this function only returns the LAST result.
    This is equivalent to chaining actions with the '>>' operator.

    Example:
    ```python
        result = await compose(action1, action2, action3).execute(context)
        # result is Ok(result3) - only the last action's result
    ```

    Args:
        *actions: Actions to compose into a single action

    Returns:
        A single Action that executes actions in sequence and returns the last result
    """
    action_list = list(actions)
    if not action_list:
        raise ValueError("Cannot compose zero actions")
    if len(action_list) == 1:
        return action_list[0]

    class ComposeAction(Action[Any]):
        async def execute(self, context: ActionContext) -> Result[Any, Exception]:
            try:
                result = await action_list[0].execute(context)
                if result.is_error():
                    return result

                for action in action_list[1:]:
                    result = await action.execute(context)
                    if result.is_error():
                        return result

                return result
            except Exception as e:
                return Error(e)

    return ComposeAction()


def identity(value: Optional[T] = None) -> Action[T]:
    """Create an identity action that returns the provided value or passes through inputs"""

    class Identity(Action[T]):
        """
        Identity action that passes its input through unchanged

        This action satisfies the identity laws of composition:
        id >> f = f and f >> id = f
        """

        def __init__(self, value: Optional[T] = None):
            self.value = value

        async def execute(self, context: ActionContext) -> Result[T, Exception]:
            if self.value is None:
                return Error(Exception("Identity action received no value"))
            return Ok(self.value)

        def with_input(self, value: Any) -> "Action[Any]":
            return Identity(value)

    return Identity(value)


def value(val: T) -> Action[T]:
    """
    Create an action that returns a constant value
    alias for identity

    Example:
    ```python
        # Create default values for branching logic
        result = await pipe(
            Query("#optional-element"),
            branch(
                lambda el: el is not None,
                ExtractText(),
                value("Default text")  # Use this if element not found
            )
        ).execute(context)
    ```

    Args:
        val: Value to return

    Returns:
        An Action that returns the value
    """
    return identity(val)
