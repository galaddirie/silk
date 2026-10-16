"""Truthfulness contracts for Playwright browser-context options."""

from __future__ import annotations

from collections.abc import Callable
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Browser
from playwright.async_api import BrowserContext as PWBrowserContext

from silk.browsers.drivers.playwright import _PlaywrightDriver
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserHttpHeaders,
    BrowserProxy,
    BrowserViewport,
)


@pytest.mark.asyncio
async def test_new_context_forwards_every_modeled_option_truthfully() -> None:
    driver = _PlaywrightDriver()
    browser = MagicMock(spec=Browser)
    native_context = MagicMock(spec=PWBrowserContext)
    browser.new_context = AsyncMock(return_value=native_context)
    driver._browser = browser
    options = BrowserContextOptions(
        viewport=BrowserViewport(width=1280, height=720),
        permissions=("geolocation",),
        user_agent="SilkContext/1.0",
        extra_http_headers=BrowserHttpHeaders({"x-silk-context": "configured"}),
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
        permissions=("geolocation",),
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
    assert outcome.ok.context_id in driver._registry.contexts
    assert not hasattr(outcome.ok, "context_ref")


@pytest.mark.parametrize(
    ("removed_name", "value"),
    (
        ("user_data_dir", "/tmp/profile"),
        ("ignore_default_args", True),
        ("args", ["--disable-gpu"]),
        ("headless", True),
        ("slow_mo", 50),
    ),
)
def test_context_options_reject_launch_persistent_and_unknown_fields(
    removed_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=removed_name):
        BrowserContextOptions(**{removed_name: value})


def test_context_options_reject_incomplete_and_negative_values() -> None:
    with pytest.raises(TypeError, match="server"):
        BrowserProxy()
    with pytest.raises(ValueError, match="non-negative"):
        BrowserContextOptions(timeout=-1)
    with pytest.raises(ValueError, match="non-negative"):
        BrowserContextOptions(navigation_timeout=-1)
    with pytest.raises(ValueError, match="positive"):
        BrowserViewport(width=0, height=600)


@pytest.mark.parametrize(
    "construct",
    (
        lambda: BrowserViewport(width="800", height=600),
        lambda: BrowserViewport(width=True, height=600),
        lambda: BrowserProxy(server=123),
        lambda: BrowserHttpHeaders({"x-value": 1}),
        lambda: BrowserContextOptions(viewport={"width": 800, "height": 600}),
        lambda: BrowserContextOptions(permissions=["geolocation"]),
        lambda: BrowserContextOptions(permissions=(1,)),
        lambda: BrowserContextOptions(extra_http_headers={"x": "value"}),
        lambda: BrowserContextOptions(proxy={"server": "http://proxy"}),
        lambda: BrowserContextOptions(user_agent=123),
        lambda: BrowserContextOptions(timeout="123"),
        lambda: BrowserContextOptions(timeout=True),
        lambda: BrowserContextOptions(navigation_timeout="123"),
        lambda: BrowserContextOptions(navigation_timeout=True),
        lambda: BrowserContextOptions(ignore_https_errors=1),
        lambda: BrowserContextOptions(java_script_enabled=0),
    ),
)
def test_context_configuration_rejects_coercible_or_wrong_runtime_types(
    construct: Callable[[], object],
) -> None:
    with pytest.raises(TypeError):
        construct()


def test_context_options_reject_runtime_subclasses_of_final_values() -> None:
    class ViewportSubclass(BrowserViewport):
        pass

    class ProxySubclass(BrowserProxy):
        pass

    class HeadersSubclass(BrowserHttpHeaders):
        pass

    with pytest.raises(TypeError, match="viewport"):
        BrowserContextOptions(viewport=ViewportSubclass(width=800, height=600))
    with pytest.raises(TypeError, match="proxy"):
        BrowserContextOptions(proxy=ProxySubclass(server="http://proxy.test"))
    with pytest.raises(TypeError, match="extra_http_headers"):
        BrowserContextOptions(extra_http_headers=HeadersSubclass({"x-test": "value"}))


def test_context_configuration_is_deeply_immutable_and_snapshot_safe() -> None:
    viewport = BrowserViewport(width=1280, height=720)
    headers = BrowserHttpHeaders({"x-silk": "original"})
    proxy = BrowserProxy(server="http://proxy.test:8080", username="silk")
    options = BrowserContextOptions(
        viewport=viewport,
        permissions=("geolocation",),
        extra_http_headers=headers,
        proxy=proxy,
        timeout=500,
    )

    with pytest.raises(FrozenInstanceError):
        options.timeout = 501
    with pytest.raises(FrozenInstanceError):
        viewport.width = 1
    with pytest.raises(TypeError):
        options.permissions[0] = "camera"
    with pytest.raises(TypeError):
        headers["x-silk"] = "mutated"
    with pytest.raises(FrozenInstanceError):
        proxy.server = "http://changed.test"

    assert options.viewport == BrowserViewport(width=1280, height=720)
    assert options.permissions == ("geolocation",)
    assert dict(options.extra_http_headers or {}) == {"x-silk": "original"}
    assert options.proxy == BrowserProxy(
        server="http://proxy.test:8080",
        username="silk",
    )
    assert copy(options) is options
    assert deepcopy(options) is options
