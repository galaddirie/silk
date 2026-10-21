"""Construction-time navigation templates over explicit dataflow operands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fp_ops import Result, result_operation_template

from silk.browsers.models import NavigationWaitLiteral, Page


def _require_non_negative_timeout(timeout: int | None) -> None:
    if timeout is not None and timeout < 0:
        raise ValueError("timeout must be non-negative")


@dataclass(frozen=True, slots=True)
class NavigateOptions:
    """Configuration for URL navigation."""

    timeout: int | None = None
    wait_until: NavigationWaitLiteral = "load"
    referer: str | None = None

    def __post_init__(self) -> None:
        _require_non_negative_timeout(self.timeout)


@dataclass(frozen=True, slots=True)
class NavigationOptions:
    """Configuration for history navigation, reload, and navigation waits."""

    timeout: int | None = None
    wait_until: NavigationWaitLiteral = "load"

    def __post_init__(self) -> None:
        _require_non_negative_timeout(self.timeout)


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


@result_operation_template
async def Navigate(
    page: Page,
    url: str,
    *,
    options: NavigateOptions | None = None,
) -> Result[Page, Exception]:
    """Navigate and preserve the exact page operand as pipeline focus."""

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
