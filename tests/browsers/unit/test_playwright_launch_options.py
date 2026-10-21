"""Native Playwright mapping for the public Chromium launch value."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from silk.browsers.drivers.playwright import PlaywrightBrowser
from silk.browsers.models import BrowserOptions, BrowserProxy


def fake_playwright(native_browser: object) -> tuple[MagicMock, MagicMock]:
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=native_browser)
    playwright.stop = AsyncMock(return_value=None)
    starter = MagicMock()
    starter.start = AsyncMock(return_value=playwright)
    return starter, playwright


@pytest.mark.asyncio
async def test_launch_forwards_every_modeled_chromium_option_exactly() -> None:
    native_browser = MagicMock()
    starter, playwright = fake_playwright(native_browser)
    options = BrowserOptions(
        headless=False,
        timeout=1_234,
        args=("--disable-gpu", "--js-flags=--expose-gc"),
        proxy=BrowserProxy(server="http://proxy.test:8080", username="silk"),
    )

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        browser = await PlaywrightBrowser.launch(options)

    assert browser._native is native_browser
    playwright.chromium.launch.assert_awaited_once_with(
        headless=False,
        timeout=1_234,
        args=["--disable-gpu", "--js-flags=--expose-gc"],
        proxy={"server": "http://proxy.test:8080", "username": "silk"},
    )


@pytest.mark.asyncio
async def test_launch_maps_defaults() -> None:
    starter, playwright = fake_playwright(MagicMock())

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        await PlaywrightBrowser.launch(BrowserOptions())

    playwright.chromium.launch.assert_awaited_once_with(
        headless=True,
        timeout=30_000,
        args=[],
        proxy=None,
    )


@pytest.mark.asyncio
async def test_failed_launch_stops_playwright_and_raises_the_cause() -> None:
    cause = RuntimeError("chromium launch failed")
    starter, playwright = fake_playwright(MagicMock())
    playwright.chromium.launch = AsyncMock(side_effect=cause)

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        with pytest.raises(RuntimeError) as raised:
            await PlaywrightBrowser.launch(BrowserOptions())

    assert raised.value is cause
    playwright.stop.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_close_stops_playwright_even_if_browser_close_fails() -> None:
    cause = RuntimeError("browser close failed")
    native_browser = MagicMock()
    native_browser.close = AsyncMock(side_effect=cause)
    playwright = MagicMock()
    playwright.stop = AsyncMock(return_value=None)
    browser = PlaywrightBrowser(playwright, native_browser)

    with pytest.raises(RuntimeError) as raised:
        await browser.close()
    await browser.close()

    assert raised.value is cause
    native_browser.close.assert_awaited_once_with()
    playwright.stop.assert_awaited_once_with()
