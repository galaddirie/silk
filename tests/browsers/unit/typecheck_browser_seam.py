# pyright: strict
"""Consumer contracts for the public browser focus and session seam."""

from __future__ import annotations

from pathlib import Path
from typing import assert_type

from fp_ops import Operation, Result, _

from silk.actions.elements import Element, ElementScope, QueryAll as query_all
from silk.actions.navigation import (
    CurrentUrl as current_url,
    Evaluate as evaluate,
    EvaluateWith as evaluate_with,
    GoBack as go_back,
    GoForward as go_forward,
    Navigate as navigate,
    NavigationOptions,
    Reload as reload,
    ScreenshotTo as screenshot_to,
    Title as title,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers import (
    Browser,
    BrowserContextOptions,
    BrowserDriver,
    BrowserOptions,
    BrowserSession,
    ElementHandle,
    LaunchedBrowser,
    Page,
)
from silk.browsers.drivers import PlaywrightDriver, attempt, attempt_blocking


async def nominal_browser_values_are_public_inputs(
    page: Page,
    element: ElementHandle,
    path: Path,
) -> None:
    page_input: Page = page
    element_input: ElementHandle = element

    navigate_page = navigate(_, "https://example.test")
    navigate_url = navigate(page, _)
    history_options = NavigationOptions(
        timeout=5_000,
        wait_until="domcontentloaded",
    )
    back_page = go_back(_, options=history_options)
    forward_page = go_forward(_, options=history_options)
    reload_page = reload(_, options=history_options)
    wait_page = wait_for_navigation(_, options=history_options)
    page_elements = query_all(".item", _)
    child_elements = query_all(".child", _)

    assert_type(
        navigate_page,
        Operation[Page, Page],
    )
    assert_type(navigate_url, Operation[str, Page])
    assert_type(back_page, Operation[Page, Page])
    assert_type(forward_page, Operation[Page, Page])
    assert_type(reload_page, Operation[Page, Page])
    assert_type(wait_page, Operation[Page, Page])
    assert_type(page_elements, Operation[ElementScope, list[Element]])
    assert_type(child_elements, Operation[ElementScope, list[Element]])

    page_outcome = await navigate_page.run(page)
    url_outcome = await navigate_url.run("https://example.test")
    back_outcome = await back_page.run(page)
    forward_outcome = await forward_page.run(page)
    reload_outcome = await reload_page.run(page)
    wait_outcome = await wait_page.run(page)
    current_outcome = await current_url(_).run(page)
    title_outcome = await title(_).run(page)
    path_outcome = await screenshot_to(page, _).run(path)
    script_outcome = await evaluate(page, _).run("return true")
    argument_outcome = await evaluate_with(page, "value => value", _).run(None)
    elements_outcome = await page_elements.run(page)
    children_outcome = await child_elements.run(element)

    assert_type(page_outcome, Result[Page, Exception])
    assert_type(url_outcome, Result[Page, Exception])
    assert_type(back_outcome, Result[Page, Exception])
    assert_type(forward_outcome, Result[Page, Exception])
    assert_type(reload_outcome, Result[Page, Exception])
    assert_type(wait_outcome, Result[Page, Exception])
    assert_type(current_outcome, Result[str, Exception])
    assert_type(title_outcome, Result[str, Exception])
    assert_type(path_outcome, Result[Path, Exception])
    assert_type(script_outcome, Result[object, Exception])
    assert_type(argument_outcome, Result[object, Exception])
    assert_type(elements_outcome, Result[list[Element], Exception])
    assert_type(children_outcome, Result[list[Element], Exception])

    assert page_input is page
    assert element_input is element


def session_selects_and_owns_its_adapter() -> None:
    _ = BrowserSession()
    _ = BrowserSession(
        options=BrowserOptions(),
        context_options=BrowserContextOptions(),
    )
    _ = BrowserSession(driver=PlaywrightDriver(package="patchright", channel="chrome"))
    _ = BrowserSession(driver=PlaywrightDriver(browser_type="firefox"))
    _ = BrowserSession(
        driver=PlaywrightDriver(package="patchright", cdp_url="ws://127.0.0.1:9222")
    )


class ReusedBrowserDriver(BrowserDriver):
    def __init__(self, browser: LaunchedBrowser) -> None:
        self._browser = browser

    async def launch(self, options: BrowserOptions) -> LaunchedBrowser:
        return self._browser


async def custom_drivers_plug_into_sessions(browser: LaunchedBrowser) -> None:
    session = BrowserSession(driver=ReusedBrowserDriver(browser))
    assert_type(session.browser, Browser)

    async def native_title() -> str:
        return "title"

    def blocking_title(prefix: str) -> str:
        return prefix + "title"

    assert_type(await attempt(native_title()), Result[str, Exception])
    assert_type(
        await attempt_blocking(blocking_title, "a "),
        Result[str, Exception],
    )
