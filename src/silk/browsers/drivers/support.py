# pyright: strict
"""Helpers for writing browser drivers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from fp_ops import Error, Ok, Result

T = TypeVar("T")
P = ParamSpec("P")


async def attempt(awaitable: Awaitable[T]) -> Result[T, Exception]:
    """Await a backend call, turning ordinary exceptions into ``Error``.

    Driver methods return ``Result`` values instead of raising; wrap each
    native call with this helper::

        async def title(self) -> Result[str, Exception]:
            return await attempt(self._native.title())
    """

    try:
        return Ok(await awaitable)
    except Exception as error:
        return Error(error)


async def attempt_blocking(
    function: Callable[P, T],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> Result[T, Exception]:
    """Run a blocking backend call in a worker thread, like :func:`attempt`.

    For synchronous libraries such as Selenium::

        async def title(self) -> Result[str, Exception]:
            return await attempt_blocking(lambda: self._driver.title)
    """

    return await attempt(asyncio.to_thread(function, *args, **kwargs))


__all__ = ["attempt", "attempt_blocking"]
