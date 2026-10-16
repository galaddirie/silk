# pyright: strict
"""Small nominal browser seam and immutable session configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Self, final, overload

from fp_ops import Result

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


class _ImmutableBrowserConfiguration:
    """Identity-preserving copy policy for immutable configuration values."""

    __slots__ = ()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self


def _require_exact_string(value: object, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")


def _require_optional_string(value: object, name: str) -> None:
    if value is not None:
        _require_exact_string(value, name)


def _require_optional_non_negative_integer(
    value: object,
    name: str,
) -> None:
    if value is None:
        return
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer or None")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


class BrowserFocus:
    """Nominal base for live browser values snapshotted by operations."""

    @final
    def __copy__(self) -> Self:
        return self

    @final
    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self


class ElementHandle(BrowserFocus, ABC):
    """Action-facing element focus with semantic pointer behavior."""

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


class Page(BrowserFocus, ABC):
    """Action-facing page focus."""

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


class BrowserContext(BrowserFocus, ABC):
    """Action-facing identity and lifecycle for one isolated context."""

    @property
    @abstractmethod
    def context_id(self) -> str: ...

    @abstractmethod
    async def new_page(self) -> Result[Page, Exception]: ...

    @abstractmethod
    async def pages(self) -> Result[list[Page], Exception]: ...

    @abstractmethod
    async def close(self) -> Result[None, Exception]: ...


@final
@dataclass(frozen=True, slots=True)
class BrowserViewport(_ImmutableBrowserConfiguration):
    """Strict immutable viewport dimensions for one browser context."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if type(self.width) is not int:
            raise TypeError("viewport width must be an integer")
        if type(self.height) is not int:
            raise TypeError("viewport height must be an integer")
        if self.width < 1:
            raise ValueError("viewport width must be positive")
        if self.height < 1:
            raise ValueError("viewport height must be positive")


@final
@dataclass(frozen=True, slots=True)
class BrowserProxy(_ImmutableBrowserConfiguration):
    """Strict immutable per-context proxy settings."""

    server: str
    bypass: str | None = None
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        _require_exact_string(self.server, "proxy server")
        _require_optional_string(self.bypass, "proxy bypass")
        _require_optional_string(self.username, "proxy username")
        _require_optional_string(self.password, "proxy password")


@final
@dataclass(frozen=True, slots=True)
class BrowserLaunchProxy(_ImmutableBrowserConfiguration):
    """Strict immutable proxy endpoint for the Chromium process."""

    server: str

    def __post_init__(self) -> None:
        _require_exact_string(self.server, "launch proxy server")


@final
@dataclass(frozen=True, slots=True)
class BrowserOptions(_ImmutableBrowserConfiguration):
    """Strict immutable Chromium process-launch configuration."""

    headless: bool = True
    timeout: int = 30_000
    args: tuple[str, ...] = ()
    proxy: BrowserLaunchProxy | None = None

    def __post_init__(self) -> None:
        if type(self.headless) is not bool:
            raise TypeError("headless must be a boolean")
        if type(self.timeout) is not int:
            raise TypeError("timeout must be an integer")
        if self.timeout < 0:
            raise ValueError("timeout must be non-negative")
        if type(self.args) is not tuple:
            raise TypeError("args must be a tuple of strings")
        for argument in self.args:
            _require_exact_string(argument, "browser argument")
        if self.proxy is not None and type(self.proxy) is not BrowserLaunchProxy:
            raise TypeError("proxy must be BrowserLaunchProxy or None")


@final
@dataclass(frozen=True, slots=True, init=False)
class BrowserHttpHeaders(_ImmutableBrowserConfiguration, Mapping[str, str]):
    """Immutable HTTP header mapping copied from construction data."""

    _items: tuple[tuple[str, str], ...]

    def __init__(self, values: Mapping[str, str] | None = None) -> None:
        if values is None:
            items: tuple[tuple[str, str], ...] = ()
        else:
            collected: list[tuple[str, str]] = []
            for name, value in values.items():
                _require_exact_string(name, "HTTP header name")
                _require_exact_string(value, f"HTTP header {name!r} value")
                collected.append((name, value))
            items = tuple(collected)
        object.__setattr__(self, "_items", items)

    def __getitem__(self, name: str) -> str:
        for item_name, value in self._items:
            if item_name == name:
                return value
        raise KeyError(name)

    def __iter__(self) -> Iterator[str]:
        return (name for name, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)


@final
@dataclass(frozen=True, slots=True)
class BrowserContextOptions(_ImmutableBrowserConfiguration):
    """Strict deeply immutable configuration for one browser context."""

    viewport: BrowserViewport | None = None
    permissions: tuple[str, ...] | None = None
    user_agent: str | None = None
    extra_http_headers: BrowserHttpHeaders | None = None
    proxy: BrowserProxy | None = None
    locale: str | None = None
    timezone_id: str | None = None
    timeout: int | None = None
    navigation_timeout: int | None = None
    ignore_https_errors: bool = False
    java_script_enabled: bool = True

    def __post_init__(self) -> None:
        if self.viewport is not None and type(self.viewport) is not BrowserViewport:
            raise TypeError("viewport must be BrowserViewport or None")
        if self.permissions is not None:
            if type(self.permissions) is not tuple:
                raise TypeError("permissions must be a tuple of strings or None")
            for permission in self.permissions:
                _require_exact_string(permission, "permission")
        _require_optional_string(self.user_agent, "user agent")
        if (
            self.extra_http_headers is not None
            and type(self.extra_http_headers) is not BrowserHttpHeaders
        ):
            raise TypeError("extra_http_headers must be BrowserHttpHeaders or None")
        if self.proxy is not None and type(self.proxy) is not BrowserProxy:
            raise TypeError("proxy must be BrowserProxy or None")
        _require_optional_string(self.locale, "locale")
        _require_optional_string(self.timezone_id, "timezone_id")
        _require_optional_non_negative_integer(self.timeout, "timeout")
        _require_optional_non_negative_integer(
            self.navigation_timeout,
            "navigation_timeout",
        )
        if type(self.ignore_https_errors) is not bool:
            raise TypeError("ignore_https_errors must be a boolean")
        if type(self.java_script_enabled) is not bool:
            raise TypeError("java_script_enabled must be a boolean")


__all__ = [
    "BrowserContext",
    "BrowserContextOptions",
    "BrowserFocus",
    "BrowserHttpHeaders",
    "BrowserLaunchProxy",
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
