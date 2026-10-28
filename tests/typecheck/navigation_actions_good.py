# pyright: strict
"""Positive typing contracts for every navigation template hole."""

from pathlib import Path
from typing import assert_type

from fp_ops import Operation, Result, _

from silk.actions.navigation import (
    Content as content,
    CurrentUrl as current_url,
    Evaluate as evaluate,
    EvaluateWith as evaluate_with,
    GoBack as go_back,
    GoForward as go_forward,
    Navigate as navigate,
    NavigateOptions,
    NavigationOptions,
    Reload as reload,
    Screenshot as screenshot,
    ScreenshotTo as screenshot_to,
    Title as title,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers.drivers.playwright import PlaywrightPage
from silk.browsers.models import Page


def every_supported_hole(
    page: Page,
    url: str,
    path: Path,
    script: str,
    argument: object,
) -> None:
    assert_type(
        navigate(_, url),
        Operation[Page, Page],
    )
    assert_type(
        navigate(page, _),
        Operation[str, Page],
    )
    assert_type(
        navigate(
            _,
            url,
            options=NavigateOptions(
                wait_until="networkidle",
                referer="https://referrer.test/source",
            ),
        ),
        Operation[Page, Page],
    )

    assert_type(go_back(_), Operation[Page, Page])
    assert_type(
        go_back(
            _,
            options=NavigationOptions(
                timeout=5_000,
                wait_until="domcontentloaded",
            ),
        ),
        Operation[Page, Page],
    )
    assert_type(go_forward(_), Operation[Page, Page])
    assert_type(
        go_forward(_, options=NavigationOptions(timeout=5_000)),
        Operation[Page, Page],
    )
    assert_type(reload(_), Operation[Page, Page])
    assert_type(
        reload(_, options=NavigationOptions(timeout=5_000)),
        Operation[Page, Page],
    )
    assert_type(
        wait_for_navigation(_),
        Operation[Page, Page],
    )
    assert_type(
        wait_for_navigation(_, options=NavigationOptions(wait_until="networkidle")),
        Operation[Page, Page],
    )
    assert_type(current_url(_), Operation[Page, str])
    assert_type(title(_), Operation[Page, str])
    assert_type(content(_), Operation[Page, str])
    assert_type(screenshot(_), Operation[Page, bytes])

    assert_type(
        screenshot_to(_, path),
        Operation[Page, Path],
    )
    assert_type(
        screenshot_to(page, _),
        Operation[Path, Path],
    )

    assert_type(
        evaluate(_, script),
        Operation[Page, object],
    )
    assert_type(
        evaluate(page, _),
        Operation[str, object],
    )

    assert_type(
        evaluate_with(_, script, argument),
        Operation[Page, object],
    )
    assert_type(
        evaluate_with(page, _, argument),
        Operation[str, object],
    )
    assert_type(
        evaluate_with(page, script, _),
        Operation[object, object],
    )
    assert_type(
        evaluate_with(_, script, None),
        Operation[Page, object],
    )


async def concrete_playwright_page_is_a_valid_input(
    page: PlaywrightPage,
    path: Path,
) -> None:
    page_effect = await navigate(_, "https://example.test").run(page)
    url_effect = await navigate(page, _).run("https://example.test")
    back_effect = await go_back(_, options=NavigationOptions(timeout=5_000)).run(page)
    forward_effect = await go_forward(_, options=NavigationOptions(timeout=5_000)).run(
        page
    )
    reload_effect = await reload(_, options=NavigationOptions(timeout=5_000)).run(page)
    wait_effect = await wait_for_navigation(
        _, options=NavigationOptions(wait_until="domcontentloaded")
    ).run(page)
    url_outcome = await current_url(_).run(page)
    title_outcome = await title(_).run(page)
    screenshot_outcome = await screenshot(_).run(page)
    path_outcome = await screenshot_to(page, _).run(path)
    script_outcome = await evaluate(page, _).run("return true")
    argument_outcome = await evaluate_with(page, "value => value", _).run(None)

    assert_type(page_effect, Result[Page, Exception])
    assert_type(url_effect, Result[Page, Exception])
    assert_type(back_effect, Result[Page, Exception])
    assert_type(forward_effect, Result[Page, Exception])
    assert_type(reload_effect, Result[Page, Exception])
    assert_type(wait_effect, Result[Page, Exception])
    assert_type(url_outcome, Result[str, Exception])
    assert_type(title_outcome, Result[str, Exception])
    assert_type(screenshot_outcome, Result[bytes, Exception])
    assert_type(path_outcome, Result[Path, Exception])
    assert_type(script_outcome, Result[object, Exception])
    assert_type(argument_outcome, Result[object, Exception])
