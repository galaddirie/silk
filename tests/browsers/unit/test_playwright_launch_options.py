"""Native Playwright mapping for the public launch value and driver settings."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from silk.browsers.drivers.playwright import PlaywrightBrowser, PlaywrightDriver
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
        browser = await PlaywrightDriver().launch(options)

    assert browser._native is native_browser
    playwright.chromium.launch.assert_awaited_once_with(
        headless=False,
        timeout=1_234,
        args=["--disable-gpu", "--js-flags=--expose-gc"],
        proxy={"server": "http://proxy.test:8080", "username": "silk"},
        channel=None,
        executable_path=None,
    )


@pytest.mark.asyncio
async def test_launch_maps_defaults() -> None:
    starter, playwright = fake_playwright(MagicMock())

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        await PlaywrightDriver().launch(BrowserOptions())

    playwright.chromium.launch.assert_awaited_once_with(
        headless=True,
        timeout=30_000,
        args=[],
        proxy=None,
        channel=None,
        executable_path=None,
    )


@pytest.mark.asyncio
async def test_driver_selects_browser_type_channel_and_executable() -> None:
    native_browser = MagicMock()
    starter, playwright = fake_playwright(native_browser)
    playwright.firefox.launch = AsyncMock(return_value=native_browser)
    driver = PlaywrightDriver(
        browser_type="firefox",
        channel="beta",
        executable_path=Path("/opt/firefox"),
    )

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        browser = await driver.launch(BrowserOptions())

    assert browser._native is native_browser
    playwright.chromium.launch.assert_not_awaited()
    playwright.firefox.launch.assert_awaited_once_with(
        headless=True,
        timeout=30_000,
        args=[],
        proxy=None,
        channel="beta",
        executable_path=Path("/opt/firefox"),
    )


@pytest.mark.asyncio
async def test_driver_loads_a_playwright_compatible_package() -> None:
    native_browser = MagicMock()
    starter, playwright = fake_playwright(native_browser)
    fork = SimpleNamespace(async_playwright=MagicMock(return_value=starter))

    with (
        patch(
            "silk.browsers.drivers.playwright.import_module",
            return_value=fork,
        ) as import_module,
        patch("silk.browsers.drivers.playwright.async_playwright") as default,
    ):
        browser = await PlaywrightDriver(package="patchright").launch(BrowserOptions())

    import_module.assert_called_once_with("patchright.async_api")
    default.assert_not_called()
    assert browser._native is native_browser
    assert browser._playwright is playwright


@pytest.mark.asyncio
async def test_failed_launch_stops_playwright_and_raises_the_cause() -> None:
    cause = RuntimeError("chromium launch failed")
    starter, playwright = fake_playwright(MagicMock())
    playwright.chromium.launch = AsyncMock(side_effect=cause)

    with (
        patch(
            "silk.browsers.drivers.playwright.async_playwright",
            return_value=starter,
        ),
        pytest.raises(RuntimeError) as raised,
    ):
        await PlaywrightDriver().launch(BrowserOptions())

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


CDP_URL = "wss://browser.test/devtools?token=secret"


@pytest.mark.asyncio
async def test_cdp_url_connects_instead_of_launching() -> None:
    native_browser = MagicMock()
    starter, playwright = fake_playwright(MagicMock())
    playwright.chromium.connect_over_cdp = AsyncMock(return_value=native_browser)

    with patch(
        "silk.browsers.drivers.playwright.async_playwright",
        return_value=starter,
    ):
        browser = await PlaywrightDriver(cdp_url=CDP_URL).launch(
            BrowserOptions(headless=False, timeout=4_321, args=("--ignored",))
        )

    playwright.chromium.launch.assert_not_awaited()
    playwright.chromium.connect_over_cdp.assert_awaited_once_with(
        CDP_URL, timeout=4_321
    )
    assert browser._native is native_browser
    assert browser._adopt_default_context


@pytest.mark.asyncio
async def test_failed_cdp_connect_stops_playwright_and_raises_the_cause() -> None:
    cause = RuntimeError("connect failed")
    starter, playwright = fake_playwright(MagicMock())
    playwright.chromium.connect_over_cdp = AsyncMock(side_effect=cause)

    with (
        patch(
            "silk.browsers.drivers.playwright.async_playwright",
            return_value=starter,
        ),
        pytest.raises(RuntimeError) as raised,
    ):
        await PlaywrightDriver(cdp_url=CDP_URL).launch(BrowserOptions())

    assert raised.value is cause
    playwright.stop.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_cdp_url_rejects_a_launch_proxy_before_starting_playwright() -> None:
    starter, _ = fake_playwright(MagicMock())

    with (
        patch(
            "silk.browsers.drivers.playwright.async_playwright",
            return_value=starter,
        ),
        pytest.raises(ValueError, match="proxy"),
    ):
        await PlaywrightDriver(cdp_url=CDP_URL).launch(
            BrowserOptions(proxy=BrowserProxy(server="http://proxy.test:8080"))
        )

    starter.start.assert_not_awaited()


@pytest.mark.parametrize(
    "settings",
    [
        {"browser_type": "firefox"},
        {"channel": "chrome"},
        {"executable_path": Path("/opt/chrome")},
    ],
)
def test_cdp_url_rejects_launch_only_driver_settings(
    settings: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="cdp_url"):
        PlaywrightDriver(cdp_url=CDP_URL, **settings)  # type: ignore[arg-type]
