"""Typed stable capabilities provided by a browser session."""

# pyright: strict

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Self, TypeAlias

from fp_ops import EnvKey, Result

from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
)

NewBrowserContext: TypeAlias = Callable[
    [BrowserContextOptions | None],
    Awaitable[Result[BrowserContext, Exception]],
]


class BrowserSessionNotStartedError(RuntimeError):
    """A captured session capability has no active browser ownership."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"browser session {session_id!r} is not started")


@dataclass(frozen=True, slots=True)
class BrowserDriverCapability:
    """Stable session-owned capability for creating browser contexts.

    The adapter handle and its umbrella close are deliberately not exposed.
    Session environments therefore cannot bypass session ownership or lock
    ordering. Captured capabilities remain safe after their session closes:
    their callback returns a typed error instead of touching a stale driver.
    """

    _new_context: NewBrowserContext

    def __post_init__(self) -> None:
        if not callable(self._new_context):
            raise TypeError("new_context must be callable")

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        """Create a context through the owning session lifecycle."""

        return await self._new_context(options)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self


@dataclass(frozen=True, slots=True)
class BrowserSessionInfo:
    """Immutable identity snapshot for a started browser session.

    Pages and browser contexts are deliberately absent. They are changing
    pipeline focus and must be passed as ordinary operation input and output.
    """

    session_id: str


@dataclass(frozen=True, slots=True)
class BrowserOptionsCapability:
    """Stable capability containing the session's immutable launch value."""

    options: BrowserOptions

    def __post_init__(self) -> None:
        if type(self.options) is not BrowserOptions:
            raise TypeError("options must be BrowserOptions")

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self


DRIVER = EnvKey("browser_driver", BrowserDriverCapability)
BROWSER_SESSION = EnvKey("browser_session", BrowserSessionInfo)
BROWSER_OPTIONS = EnvKey("browser_options", BrowserOptionsCapability)


__all__ = [
    "BROWSER_OPTIONS",
    "BROWSER_SESSION",
    "DRIVER",
    "BrowserDriverCapability",
    "BrowserOptionsCapability",
    "BrowserSessionInfo",
    "BrowserSessionNotStartedError",
    "NewBrowserContext",
]
