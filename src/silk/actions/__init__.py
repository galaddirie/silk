"""
Actions are the building blocks of Silk.

They represent pure operations that can be composed together using functional
programming patterns. Each action returns a Result type that handles both success
and error cases.

Silk provides several ways to compose actions:

- sequence: Executes actions in sequence and returns ALL results as a Block
- compose: Executes actions in sequence and returns ONLY the LAST result
- pipe: Creates a pipeline where each action can use the result of the previous action
- parallel: Executes actions concurrently and collects all results
- fallback: Tries actions in sequence until one succeeds

These can also be used through operators:
- a >> b: Equivalent to compose(a, b)
- a | b: Equivalent to fallback(a, b)
- a & b: Similar to parallel(a, b) but returns a tuple of results
"""

from silk.actions.base import Action
from silk.actions.composition import compose, fallback, parallel, pipe, sequence
from silk.actions.flow import (
    branch,
    loop_until,
    retry,
    retry_with_backoff,
    tap,
    with_timeout,
)

__all__ = [
    "Action",
    # Control
    "branch",
    "loop_until",
    "retry_with_backoff",
    "with_timeout",
    "tap",
    "retry",
    # Composition
    "sequence",
    "parallel",
    "pipe",
    "fallback",
    "compose",
]
