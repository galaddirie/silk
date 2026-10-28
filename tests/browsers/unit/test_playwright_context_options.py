"""Truthfulness contracts for Playwright browser-context options."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Browser, BrowserContext as PWBrowserContext

from silk.browsers.drivers.playwright import PlaywrightBrowser
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserProxy,
    BrowserViewport,
)


@pytest.mark.asyncio
async def test_new_context_forwards_every_modeled_option_truthfully() -> None:
    browser = MagicMock(spec=Browser)
    native_context = MagicMock(spec=PWBrowserContext)
    browser.new_context = AsyncMock(return_value=native_context)
    driver = PlaywrightBrowser(MagicMock(), browser)
    options = BrowserContextOptions(
        viewport=BrowserViewport(width=1280, height=720),
        permissions=("geolocation",),
        user_agent="SilkContext/1.0",
        extra_http_headers={"x-silk-context": "configured"},
        proxy=BrowserProxy(
            server="http://proxy.test:8080",
            bypass="localhost",
            username="silk",
            password="secret",
        ),
        locale="fr-CA",
        timezone_id="America/Toronto",
        timeout=321,
        navigation_timeout=654,
        ignore_https_errors=True,
        java_script_enabled=False,
    )

    outcome = await driver.new_context(options)

    assert outcome.is_ok()
    browser.new_context.assert_awaited_once_with(
        viewport={"width": 1280, "height": 720},
        permissions=["geolocation"],
        user_agent="SilkContext/1.0",
        extra_http_headers={"x-silk-context": "configured"},
        proxy={
            "server": "http://proxy.test:8080",
            "bypass": "localhost",
            "username": "silk",
            "password": "secret",
        },
        locale="fr-CA",
        timezone_id="America/Toronto",
        ignore_https_errors=True,
        java_script_enabled=False,
    )
    native_context.set_default_timeout.assert_called_once_with(321)
    native_context.set_default_navigation_timeout.assert_called_once_with(654)


@pytest.mark.asyncio
async def test_new_context_after_close_returns_an_error() -> None:
    browser = MagicMock(spec=Browser)
    browser.close = AsyncMock(return_value=None)
    playwright = MagicMock()
    playwright.stop = AsyncMock(return_value=None)
    driver = PlaywrightBrowser(playwright, browser)

    await driver.close()
    outcome = await driver.new_context()

    assert outcome.is_error()
    assert isinstance(outcome.error, RuntimeError)
    browser.new_context.assert_not_called()


def test_context_options_reject_incomplete_and_negative_values() -> None:
    with pytest.raises(TypeError, match="server"):
        BrowserProxy()  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="non-negative"):
        BrowserContextOptions(timeout=-1)
    with pytest.raises(ValueError, match="non-negative"):
        BrowserContextOptions(navigation_timeout=-1)
    with pytest.raises(ValueError, match="positive"):
        BrowserViewport(width=0, height=600)


def test_context_options_are_frozen_and_copy_headers() -> None:
    headers = {"x-silk": "original"}
    options = BrowserContextOptions(
        viewport=BrowserViewport(width=1280, height=720),
        extra_http_headers=headers,
        timeout=500,
    )
    headers["x-silk"] = "mutated"

    with pytest.raises(FrozenInstanceError):
        options.timeout = 501  # type: ignore[misc]
    with pytest.raises(TypeError):
        options.extra_http_headers["x-silk"] = "changed"  # type: ignore[index]
    assert dict(options.extra_http_headers or {}) == {"x-silk": "original"}
