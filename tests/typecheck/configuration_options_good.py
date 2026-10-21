"""Positive static contracts for immutable browser configuration values."""

from __future__ import annotations

from typing import assert_type

from silk.actions.elements import WaitOptions
from silk.actions.navigation import NavigateOptions, NavigationOptions
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserOptions,
    BrowserProxy,
    BrowserViewport,
)

launch_proxy = BrowserProxy(server="http://proxy.test:8080")
context_proxy = BrowserProxy(
    server="http://proxy.test:8080",
    bypass="localhost",
    username="silk",
    password="secret",
)
launch_options = BrowserOptions(
    headless=True,
    timeout=10_000,
    args=("--disable-gpu",),
    proxy=launch_proxy,
)
context_options = BrowserContextOptions(
    viewport=BrowserViewport(width=1280, height=720),
    permissions=("geolocation",),
    user_agent="Silk/1.0",
    extra_http_headers={"x-silk": "configured"},
    proxy=context_proxy,
    locale="fr-CA",
    timezone_id="America/Toronto",
    timeout=500,
    navigation_timeout=1_000,
    ignore_https_errors=True,
    java_script_enabled=False,
)
navigate_options = NavigateOptions(
    timeout=2_000,
    wait_until="networkidle",
    referer="https://referrer.test",
)
navigation_options = NavigationOptions(
    timeout=2_000,
    wait_until="domcontentloaded",
)
wait_options = WaitOptions(timeout=250, state="attached")

assert_type(launch_options, BrowserOptions)
assert_type(context_options, BrowserContextOptions)
assert_type(navigate_options, NavigateOptions)
assert_type(navigation_options, NavigationOptions)
assert_type(wait_options, WaitOptions)
