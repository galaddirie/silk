"""Playwright navigation mapping through public action templates."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import _
from playwright.async_api import Browser
from playwright.async_api import BrowserContext as PWBrowserContext
from playwright.async_api import Page as PWPage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from silk.actions.navigation import (
    NavigateOptions,
    NavigationOptions,
    GoBack as go_back,
    Navigate as navigate,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers.drivers.playwright import _PlaywrightDriver
from silk.browsers.models import Page


async def public_page() -> tuple[Page, MagicMock, MagicMock]:
    driver = _PlaywrightDriver()
    browser = MagicMock(spec=Browser)
    context = MagicMock(spec=PWBrowserContext)
    native_page = MagicMock(spec=PWPage)
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=native_page)
    context.pages = [native_page]
    native_page.goto = AsyncMock(return_value=None)
    native_page.go_back = AsyncMock(return_value=None)
    navigation_waiter = MagicMock()
    navigation_waiter.__aenter__ = AsyncMock(return_value=None)
    navigation_waiter.__aexit__ = AsyncMock(return_value=None)
    native_page.expect_navigation = MagicMock(return_value=navigation_waiter)
    driver._browser = browser

    context_result = await driver.new_context()
    assert context_result.is_ok()
    page_result = await context_result.ok.new_page()
    assert page_result.is_ok()
    return page_result.ok, native_page, navigation_waiter


@pytest.mark.asyncio
async def test_url_navigation_maps_only_its_typed_configuration() -> None:
    page, native_page, _navigation_waiter = await public_page()
    options = NavigateOptions(
        timeout=321,
        wait_until="domcontentloaded",
        referer="https://referrer.test/source",
    )

    result = await navigate(_, "https://target.test", options=options).run(page)

    assert result.ok is page
    native_page.goto.assert_awaited_once_with(
        "https://target.test",
        wait_until="domcontentloaded",
        timeout=321,
        referer="https://referrer.test/source",
    )


@pytest.mark.asyncio
async def test_history_and_load_wait_map_their_typed_configuration() -> None:
    page, native_page, navigation_waiter = await public_page()
    options = NavigationOptions(timeout=654, wait_until="networkidle")

    back = await go_back(_, options=options).run(page)
    waited = await wait_for_navigation(_, options=options).run(page)

    assert back.ok is page
    assert waited.ok is page
    native_page.go_back.assert_awaited_once_with(
        wait_until="networkidle",
        timeout=654,
    )
    native_page.expect_navigation.assert_called_once_with(
        wait_until="networkidle",
        timeout=654,
    )
    navigation_waiter.__aenter__.assert_awaited_once_with()
    navigation_waiter.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_native_navigation_exception_survives_action_unchanged() -> None:
    page, native_page, _navigation_waiter = await public_page()
    native_error = RuntimeError("navigation aborted")
    native_page.goto.side_effect = native_error

    result = await navigate(_, "https://target.test").run(page)

    assert result.is_error()
    assert result.error is native_error


@pytest.mark.asyncio
async def test_navigation_wait_preserves_native_timeout_unchanged() -> None:
    page, _native_page, navigation_waiter = await public_page()
    native_timeout = PlaywrightTimeoutError("future navigation timed out")
    navigation_waiter.__aexit__.side_effect = native_timeout

    result = await wait_for_navigation(_).run(page)

    assert result.is_error()
    assert result.error is native_timeout
