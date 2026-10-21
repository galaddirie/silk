# pyright: strict
"""Browser interfaces and immutable browser configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Literal, overload

from fp_ops import EnvKey, Result

CoordinateType = tuple[int, int]
MouseButtonLiteral = Literal["left", "middle", "right"]
WaitStateLiteral = Literal["visible", "hidden", "attached", "detached"]
NavigationWaitLiteral = Literal["load", "domcontentloaded", "networkidle"]
_NO_EVALUATION_ARGUMENT = object()


class KeyModifier(Enum):
    """Keyboard modifiers accepted by element pointer actions."""

    NONE = 0
    ALT = 1
    CTRL = 2
    COMMAND = 4
    SHIFT = 8


class ElementHandle(ABC):
    """A live element on a page."""

    @property
    @abstractmethod
    def page_id(self) -> str: ...

    @property
    @abstractmethod
    def context_id(self) -> str: ...

    @property
    @abstractmethod
    def selector(self) -> str | None: ...

    @abstractmethod
    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]: ...

    @abstractmethod
    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]: ...

    @abstractmethod
    async def click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        click_count: int = 1,
        force: bool = False,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def double_click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        force: bool = False,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def fill(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear: bool = False,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def type(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def select(
        self,
        *,
        value: str | None = None,
        text: str | None = None,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def scroll_into_view(self) -> Result[None, Exception]: ...

    @abstractmethod
    async def text(self) -> Result[str, Exception]: ...

    @abstractmethod
    async def inner_text(self) -> Result[str, Exception]: ...

    @abstractmethod
    async def html(self, *, outer: bool = True) -> Result[str, Exception]: ...

    @abstractmethod
    async def attribute(
        self,
        name: str,
    ) -> Result[str | None, Exception]: ...

    @abstractmethod
    async def move_pointer_to(
        self,
        *,
        offset: CoordinateType = (0, 0),
        center: bool = True,
        steps: int = 1,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def drag_to(
        self,
        target: ElementHandle,
        *,
        steps: int = 1,
        move_to_center: bool = True,
        position_offset: CoordinateType | None = None,
        source_offset: CoordinateType | None = None,
        target_offset: CoordinateType | None = None,
    ) -> Result[None, Exception]: ...


class Page(ABC):
    """A live browser page."""

    @property
    @abstractmethod
    def page_id(self) -> str: ...

    @property
    @abstractmethod
    def context_id(self) -> str: ...

    @abstractmethod
    async def navigate(
        self,
        url: str,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
        referer: str | None = None,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def url(self) -> Result[str, Exception]: ...

    @abstractmethod
    async def title(self) -> Result[str, Exception]: ...

    @abstractmethod
    async def content(self) -> Result[str, Exception]: ...

    @abstractmethod
    async def reload(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def wait_for_navigation(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        """Wait for the next main-frame navigation and its load state."""

        ...

    @abstractmethod
    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]: ...

    @abstractmethod
    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]: ...

    @abstractmethod
    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout_ms: int | None = None,
        state: WaitStateLiteral = "visible",
    ) -> Result[ElementHandle | None, Exception]: ...

    @overload
    async def evaluate(self, script: str) -> Result[object, Exception]: ...

    @overload
    async def evaluate(
        self,
        script: str,
        argument: object,
    ) -> Result[object, Exception]: ...

    @abstractmethod
    async def evaluate(
        self,
        script: str,
        argument: object = _NO_EVALUATION_ARGUMENT,
    ) -> Result[object, Exception]: ...

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]: ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]: ...

    @abstractmethod
    async def screenshot(
        self,
        path: Path | None = None,
    ) -> Result[Path | bytes, Exception]: ...

    @abstractmethod
    async def mouse_move(
        self,
        x: float,
        y: float,
        *,
        steps: int = 1,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def mouse_down(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def mouse_up(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def key_press(
        self,
        key: str,
        *,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def key_down(self, key: str) -> Result[None, Exception]: ...

    @abstractmethod
    async def key_up(self, key: str) -> Result[None, Exception]: ...

    @abstractmethod
    async def scroll(
        self,
        *,
        x: int = 0,
        y: int = 0,
    ) -> Result[None, Exception]: ...

    @abstractmethod
    async def close(self) -> Result[None, Exception]: ...


class BrowserContext(ABC):
    """One isolated browser context (cookies, storage, pages)."""

    @property
    @abstractmethod
    def context_id(self) -> str: ...

    @abstractmethod
    async def new_page(self) -> Result[Page, Exception]: ...

    @abstractmethod
    async def pages(self) -> Result[list[Page], Exception]: ...

    @abstractmethod
    async def close(self) -> Result[None, Exception]: ...


class Browser(ABC):
    """A running browser that pipelines can open new contexts in.

    Closing the browser is owned by :class:`~silk.browsers.sessions.BrowserSession`,
    so it is deliberately not part of this interface.
    """

    @abstractmethod
    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]: ...


BROWSER = EnvKey("browser", Browser)  # type: ignore[type-abstract]
"""Environment key under which a session provides its :class:`Browser`."""


@dataclass(frozen=True, slots=True)
class BrowserViewport:
    """Viewport dimensions for one browser context."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("viewport width and height must be positive")


@dataclass(frozen=True, slots=True)
class BrowserProxy:
    """Proxy settings for the browser process or one context."""

    server: str
    bypass: str | None = None
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserOptions:
    """Chromium process-launch configuration."""

    headless: bool = True
    timeout: int = 30_000
    args: tuple[str, ...] = ()
    proxy: BrowserProxy | None = None

    def __post_init__(self) -> None:
        if self.timeout < 0:
            raise ValueError("timeout must be non-negative")


@dataclass(frozen=True, slots=True)
class BrowserContextOptions:
    """Configuration for one browser context.

    ``extra_http_headers`` is copied into a read-only mapping on construction.
    """

    viewport: BrowserViewport | None = None
    permissions: tuple[str, ...] | None = None
    user_agent: str | None = None
    extra_http_headers: Mapping[str, str] | None = None
    proxy: BrowserProxy | None = None
    locale: str | None = None
    timezone_id: str | None = None
    timeout: int | None = None
    navigation_timeout: int | None = None
    ignore_https_errors: bool = False
    java_script_enabled: bool = True

    def __post_init__(self) -> None:
        if self.extra_http_headers is not None:
            object.__setattr__(
                self,
                "extra_http_headers",
                MappingProxyType(dict(self.extra_http_headers)),
            )
        if self.timeout is not None and self.timeout < 0:
            raise ValueError("timeout must be non-negative")
        if self.navigation_timeout is not None and self.navigation_timeout < 0:
            raise ValueError("navigation_timeout must be non-negative")


__all__ = [
    "BROWSER",
    "Browser",
    "BrowserContext",
    "BrowserContextOptions",
    "BrowserOptions",
    "BrowserProxy",
    "BrowserViewport",
    "CoordinateType",
    "ElementHandle",
    "KeyModifier",
    "MouseButtonLiteral",
    "NavigationWaitLiteral",
    "Page",
    "WaitStateLiteral",
]
