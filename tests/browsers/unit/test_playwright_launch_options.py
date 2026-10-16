"""Native Playwright mapping for the public Chromium launch value."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from silk.browsers.drivers.playwright import _PlaywrightDriver
from silk.browsers.models import BrowserLaunchProxy, BrowserOptions


@pytest.mark.asyncio
async def test_launch_forwards_every_modeled_chromium_option_exactly() -> None:
    native_browser = object()
    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=native_browser)
    playwright = MagicMock()
    playwright.chromium = chromium
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=playwright)
    options = BrowserOptions(
        headless=False,
        timeout=1_234,
        args=("--disable-gpu", "--js-flags=--expose-gc"),
        proxy=BrowserLaunchProxy(server="http://proxy.test:8080"),
    )
    driver = _PlaywrightDriver()

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=manager,
    ):
        outcome = await driver.launch(options)

    assert outcome.is_ok(), outcome
    assert driver._browser is native_browser
    chromium.launch.assert_awaited_once_with(
        headless=False,
        timeout=1_234,
        args=("--disable-gpu", "--js-flags=--expose-gc"),
        proxy={
            "server": "http://proxy.test:8080",
        },
    )


@pytest.mark.asyncio
async def test_launch_maps_explicit_defaults_without_speculative_modes() -> None:
    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=object())
    playwright = MagicMock()
    playwright.chromium = chromium
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=playwright)
    driver = _PlaywrightDriver()

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=manager,
    ):
        outcome = await driver.launch()

    assert outcome.is_ok(), outcome
    chromium.launch.assert_awaited_once_with(
        headless=True,
        timeout=30_000,
        args=(),
        proxy=None,
    )


@pytest.mark.asyncio
async def test_repeated_launch_rejects_without_overwriting_live_ownership() -> None:
    native_browser = object()
    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=native_browser)
    playwright = MagicMock()
    playwright.chromium = chromium
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=playwright)
    driver = _PlaywrightDriver()

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=manager,
    ) as manager_factory:
        first = await driver.launch()
        repeated = await driver.launch()

    assert first.is_ok(), first
    assert repeated.is_error()
    assert isinstance(repeated.error, RuntimeError)
    assert "already launched" in str(repeated.error)
    assert driver._browser is native_browser
    manager_factory.assert_called_once_with()
    manager.__aenter__.assert_awaited_once_with()
    chromium.launch.assert_awaited_once_with(
        headless=True,
        timeout=30_000,
        args=(),
        proxy=None,
    )


@pytest.mark.asyncio
async def test_relaunch_requires_a_fully_successful_close_and_preserves_cause() -> None:
    close_cause = RuntimeError("browser close failed")
    first_browser = MagicMock()
    first_browser.close = AsyncMock(side_effect=[close_cause, None])
    second_browser = MagicMock()
    second_browser.close = AsyncMock(return_value=None)

    first_chromium = MagicMock()
    first_chromium.launch = AsyncMock(return_value=first_browser)
    first_playwright = MagicMock()
    first_playwright.chromium = first_chromium
    first_manager = MagicMock()
    first_manager.__aenter__ = AsyncMock(return_value=first_playwright)
    first_manager.__aexit__ = AsyncMock(return_value=None)

    second_chromium = MagicMock()
    second_chromium.launch = AsyncMock(return_value=second_browser)
    second_playwright = MagicMock()
    second_playwright.chromium = second_chromium
    second_manager = MagicMock()
    second_manager.__aenter__ = AsyncMock(return_value=second_playwright)
    second_manager.__aexit__ = AsyncMock(return_value=None)
    driver = _PlaywrightDriver()

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        side_effect=[first_manager, second_manager],
    ):
        assert (await driver.launch()).is_ok()
        failed_close = await driver.close()
        rejected = await driver.launch()
        assert (await driver.close()).is_ok()
        relaunched = await driver.launch()
        final_close = await driver.close()

    assert failed_close.is_error()
    assert failed_close.error is close_cause
    assert rejected.is_error()
    assert isinstance(rejected.error, RuntimeError)
    assert relaunched.is_ok(), relaunched
    assert final_close.is_ok(), final_close
    first_chromium.launch.assert_awaited_once()
    second_chromium.launch.assert_awaited_once()
    assert first_browser.close.await_count == 2
    second_browser.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_partial_launch_ownership_must_be_settled_before_relaunch() -> None:
    launch_cause = RuntimeError("chromium launch failed")
    first_chromium = MagicMock()
    first_chromium.launch = AsyncMock(side_effect=launch_cause)
    first_playwright = MagicMock()
    first_playwright.chromium = first_chromium
    first_manager = MagicMock()
    first_manager.__aenter__ = AsyncMock(return_value=first_playwright)
    first_manager.__aexit__ = AsyncMock(return_value=None)

    second_browser = MagicMock()
    second_browser.close = AsyncMock(return_value=None)
    second_chromium = MagicMock()
    second_chromium.launch = AsyncMock(return_value=second_browser)
    second_playwright = MagicMock()
    second_playwright.chromium = second_chromium
    second_manager = MagicMock()
    second_manager.__aenter__ = AsyncMock(return_value=second_playwright)
    second_manager.__aexit__ = AsyncMock(return_value=None)
    driver = _PlaywrightDriver()

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        side_effect=[first_manager, second_manager],
    ) as manager_factory:
        failed = await driver.launch()
        rejected = await driver.launch()
        settled = await driver.close()
        relaunched = await driver.launch()
        final_close = await driver.close()

    assert failed.is_error()
    assert failed.error is launch_cause
    assert rejected.is_error()
    assert isinstance(rejected.error, RuntimeError)
    assert settled.is_ok(), settled
    assert relaunched.is_ok(), relaunched
    assert final_close.is_ok(), final_close
    assert manager_factory.call_count == 2
    first_manager.__aexit__.assert_awaited_once_with(None, None, None)
    second_browser.close.assert_awaited_once_with()
