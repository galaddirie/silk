"""Construction-time navigation templates over explicit dataflow operands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self, final

from fp_ops import Error, Result, result_operation_template

from silk.browsers.models import NavigationWaitLiteral, Page


class _ImmutableNavigationConfiguration:
    __slots__ = ()

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self


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


def _require_wait_until(value: object) -> None:
    if type(value) is not str:
        raise TypeError("wait_until must be a string")
    if value not in ("load", "domcontentloaded", "networkidle"):
        raise ValueError("wait_until must be load, domcontentloaded, or networkidle")


@final
@dataclass(frozen=True, slots=True)
class NavigateOptions(_ImmutableNavigationConfiguration):
    """Strict immutable configuration consumed only by URL navigation."""

    timeout: int | None = None
    wait_until: NavigationWaitLiteral = "load"
    referer: str | None = None

    def __post_init__(self) -> None:
        _require_optional_non_negative_integer(self.timeout, "timeout")
        _require_wait_until(self.wait_until)
        if self.referer is not None and type(self.referer) is not str:
            raise TypeError("referer must be a string or None")


@final
@dataclass(frozen=True, slots=True)
class NavigationOptions(_ImmutableNavigationConfiguration):
    """Strict immutable history and load-state configuration."""

    timeout: int | None = None
    wait_until: NavigationWaitLiteral = "load"

    def __post_init__(self) -> None:
        _require_optional_non_negative_integer(self.timeout, "timeout")
        _require_wait_until(self.wait_until)


__all__ = [
    "Content",
    "CurrentUrl",
    "Evaluate",
    "EvaluateWith",
    "GoBack",
    "GoForward",
    "NavigateOptions",
    "NavigationOptions",
    "Navigate",
    "Reload",
    "Screenshot",
    "ScreenshotTo",
    "Title",
    "WaitForNavigation",
]


def _require_navigate_options(options: object) -> TypeError | None:
    if options is not None and type(options) is not NavigateOptions:
        return TypeError("options must be NavigateOptions or None")
    return None


def _require_navigation_options(options: object) -> TypeError | None:
    if options is not None and type(options) is not NavigationOptions:
        return TypeError("options must be NavigationOptions or None")
    return None


@result_operation_template
async def Navigate(
    page: Page,
    url: str,
    *,
    options: NavigateOptions | None = None,
) -> Result[Page, Exception]:
    """Navigate and preserve the exact page operand as pipeline focus."""

    if error := _require_navigate_options(options):
        return Error(error)
    configured = options if options is not None else NavigateOptions()
    outcome = await page.navigate(
        url,
        timeout_ms=configured.timeout,
        wait_until=configured.wait_until,
        referer=configured.referer,
    )
    return outcome.map(lambda _ignored: page)


@result_operation_template
async def GoBack(
    page: Page,
    *,
    options: NavigationOptions | None = None,
) -> Result[Page, Exception]:
    """Navigate backward and preserve the exact page operand as focus."""

    if error := _require_navigation_options(options):
        return Error(error)
    configured = options if options is not None else NavigationOptions()
    outcome = await page.go_back(
        timeout_ms=configured.timeout,
        wait_until=configured.wait_until,
    )
    return outcome.map(lambda _ignored: page)


@result_operation_template
async def GoForward(
    page: Page,
    *,
    options: NavigationOptions | None = None,
) -> Result[Page, Exception]:
    """Navigate forward and preserve the exact page operand as focus."""

    if error := _require_navigation_options(options):
        return Error(error)
    configured = options if options is not None else NavigationOptions()
    outcome = await page.go_forward(
        timeout_ms=configured.timeout,
        wait_until=configured.wait_until,
    )
    return outcome.map(lambda _ignored: page)


@result_operation_template
async def Reload(
    page: Page,
    *,
    options: NavigationOptions | None = None,
) -> Result[Page, Exception]:
    """Reload and preserve the exact page operand as focus."""

    if error := _require_navigation_options(options):
        return Error(error)
    configured = options if options is not None else NavigationOptions()
    outcome = await page.reload(
        timeout_ms=configured.timeout,
        wait_until=configured.wait_until,
    )
    return outcome.map(lambda _ignored: page)


@result_operation_template
async def WaitForNavigation(
    page: Page,
    *,
    options: NavigationOptions | None = None,
) -> Result[Page, Exception]:
    """Wait for the next main-frame navigation and preserve page focus."""

    if error := _require_navigation_options(options):
        return Error(error)
    configured = options if options is not None else NavigationOptions()
    outcome = await page.wait_for_navigation(
        timeout_ms=configured.timeout,
        wait_until=configured.wait_until,
    )
    return outcome.map(lambda _ignored: page)


@result_operation_template
async def CurrentUrl(page: Page) -> Result[str, Exception]:
    """Read the current page URL."""

    return await page.url()


@result_operation_template
async def Title(page: Page) -> Result[str, Exception]:
    """Read the current page title."""

    return await page.title()


@result_operation_template
async def Content(page: Page) -> Result[str, Exception]:
    """Read the current page HTML content."""

    return await page.content()


@result_operation_template
async def Screenshot(page: Page) -> Result[bytes, Exception]:
    """Capture the page as bytes."""

    return await page.screenshot()


@result_operation_template
async def ScreenshotTo(
    page: Page,
    path: Path,
) -> Result[Path, Exception]:
    """Capture the page to the path dataflow operand."""

    return await page.screenshot(path)


@result_operation_template
async def Evaluate(
    page: Page,
    script: str,
) -> Result[object, Exception]:
    """Evaluate a script dataflow operand without a browser argument."""

    outcome: Result[object, Exception] = await page.evaluate(script)
    return outcome


@result_operation_template
async def EvaluateWith(
    page: Page,
    script: str,
    argument: object,
) -> Result[object, Exception]:
    """Evaluate a script with exactly one browser argument, including ``None``."""

    outcome: Result[object, Exception] = await page.evaluate(script, argument)
    return outcome
