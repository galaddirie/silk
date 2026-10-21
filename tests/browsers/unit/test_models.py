"""Strict immutable browser and action configuration contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from silk.actions.elements import WaitOptions
from silk.actions.navigation import NavigateOptions, NavigationOptions
from silk.browsers.models import BrowserOptions, BrowserProxy


def test_browser_options_are_the_small_truthful_chromium_launch_model() -> None:
    proxy = BrowserProxy(server="http://proxy.test:8080")
    options = BrowserOptions(
        headless=False,
        timeout=12_345,
        args=("--disable-gpu", "--window-size=777,555"),
        proxy=proxy,
    )

    assert options.headless is False
    assert options.timeout == 12_345
    assert options.args == ("--disable-gpu", "--window-size=777,555")
    assert options.proxy is proxy

    with pytest.raises(FrozenInstanceError):
        options.timeout = 1


@pytest.mark.parametrize(
    ("removed_name", "value"),
    (
        ("browser_type", "chromium"),
        ("viewport_width", 777),
        ("viewport_height", 555),
        ("navigation_timeout", 1_000),
        ("wait_timeout", 1_000),
        ("stealth_mode", True),
        ("user_agent", "Legacy/1.0"),
        ("extra_http_headers", {"x-test": "legacy"}),
        ("ignore_https_errors", True),
        ("disable_javascript", True),
        ("browser_args", ["--disable-gpu"]),
        ("extra_args", {"slow_mo": 50}),
        ("locale", "fr-CA"),
        ("timezone", "America/Toronto"),
        ("remote_url", "ws://browser.test"),
    ),
)
def test_browser_options_reject_every_unsupported_legacy_field(
    removed_name: str,
    value: object,
) -> None:
    with pytest.raises(TypeError, match=removed_name):
        BrowserOptions(**{removed_name: value})


@pytest.mark.parametrize(
    "construct",
    (lambda: BrowserOptions(timeout=-1),),
)
def test_browser_options_reject_invalid_values(
    construct: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        construct()


def test_navigation_and_wait_options_are_frozen_values() -> None:
    navigate = NavigateOptions(
        timeout=4_000,
        wait_until="networkidle",
        referer="https://referrer.test",
    )
    navigation = NavigationOptions(
        timeout=4_000,
        wait_until="domcontentloaded",
    )
    wait = WaitOptions(timeout=250, state="attached")

    with pytest.raises(FrozenInstanceError):
        navigate.referer = "https://changed.test"
    with pytest.raises(FrozenInstanceError):
        navigation.timeout = 1
    with pytest.raises(FrozenInstanceError):
        wait.state = "hidden"


@pytest.mark.parametrize(
    "construct",
    (
        lambda: NavigateOptions(timeout=-1),
        lambda: NavigateOptions(unknown=True),
        lambda: NavigationOptions(timeout=-1),
        lambda: NavigationOptions(referer="https://impossible.test"),
        lambda: WaitOptions(timeout=-1),
        lambda: WaitOptions(poll_interval=10),
    ),
)
def test_navigation_and_wait_options_reject_invalid_values_and_extras(
    construct: Callable[[], object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        construct()


def test_browser_models_do_not_publish_native_translation_records() -> None:
    import silk.browsers.models as models

    for stale_name in (
        "ActionOptions",
        "BaseInputOptions",
        "MouseButton",
        "MouseOptions",
        "PointerEventType",
        "RetryOptions",
        "SelectOptions",
        "TypeOptions",
        "WaitUntilOptions",
    ):
        assert not hasattr(models, stale_name)
