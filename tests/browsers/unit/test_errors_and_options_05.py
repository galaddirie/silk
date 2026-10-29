from __future__ import annotations

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from silk.actions.input import ClickOptions
from silk.browsers.drivers.playwright import translate_error
from silk.browsers.models import RequestBlocking
from silk.errors import (
    AttributeNotFoundError,
    BrowserError,
    BrowserTimeoutError,
    ElementNotFoundError,
    NavigationError,
    NotFoundError,
    PageNotFoundError,
    TargetClosedError,
)
from silk.selectors import SELF, SelectorGroup, css


def fork_error(name: str, *, base: type[Exception] = Exception) -> Exception:
    """An exception class shaped like a Playwright fork's (own module, same name)."""

    cls = type(name, (base,), {})
    cls.__module__ = "patchright._impl._errors"
    return cls("native message")


def test_playwright_errors_translate_and_keep_the_cause() -> None:
    timeout = PlaywrightTimeoutError("slow")
    translated = translate_error(timeout)
    assert isinstance(translated, BrowserTimeoutError)
    assert isinstance(translated, TimeoutError)
    assert translated.__cause__ is timeout

    generic = translate_error(PlaywrightError("boom"))
    assert type(generic) is BrowserError

    navigation = translate_error(PlaywrightError("refused"), navigation_url="https://x.test")
    assert isinstance(navigation, NavigationError)
    assert navigation.url == "https://x.test"


def test_fork_errors_translate_by_class_name() -> None:
    assert isinstance(translate_error(fork_error("TimeoutError")), BrowserTimeoutError)
    assert isinstance(translate_error(fork_error("TargetClosedError")), TargetClosedError)
    assert type(translate_error(fork_error("Error"))) is BrowserError


def test_foreign_errors_pass_through_unchanged() -> None:
    error = RuntimeError("not from playwright")
    assert translate_error(error) is error
    assert translate_error(error, navigation_url="https://x.test") is error


def test_not_found_hierarchy() -> None:
    for error in (
        ElementNotFoundError("#x"),
        AttributeNotFoundError("#x", "href"),
        PageNotFoundError("p", "c"),
    ):
        assert isinstance(error, NotFoundError)
        assert isinstance(error, LookupError)


def test_request_blocking() -> None:
    blocking = RequestBlocking(
        resource_types=frozenset({"image", "font"}),
        url_patterns=("*://ads.example/*", "*.mp4"),
    )
    assert blocking.blocks("image", "https://site/a.png")
    assert blocking.blocks("script", "https://ads.example/x.js")
    assert blocking.blocks("media", "https://site/v.mp4")
    assert not blocking.blocks("document", "https://site/")
    with pytest.raises(ValueError, match="document"):
        RequestBlocking(resource_types=frozenset({"document"}))


def test_self_is_not_a_group_fallback_and_click_position_is_validated() -> None:
    with pytest.raises(ValueError, match="SELF"):
        SelectorGroup("bad", css("a"), SELF)
    with pytest.raises(ValueError, match="position"):
        ClickOptions(position=(-1, 0))
    assert ClickOptions(position=(3.5, 2)).position == (3.5, 2)
