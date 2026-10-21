"""Runtime contracts for navigation operation templates."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import overload
from unittest.mock import MagicMock
from urllib.parse import quote

import pytest
from fp_ops import Error, Ok, Result, _

from silk.actions import navigation
from silk.actions.navigation import (
    NavigateOptions,
    NavigationOptions,
    Content as content,
    CurrentUrl as current_url,
    Evaluate as evaluate,
    EvaluateWith as evaluate_with,
    GoBack as go_back,
    GoForward as go_forward,
    Navigate as navigate,
    Reload as reload,
    Screenshot as screenshot,
    ScreenshotTo as screenshot_to,
    Title as title,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers.models import (
    BrowserOptions,
    Page,
)
from silk.browsers.sessions import BrowserSession

_NO_SCRIPT_ARGUMENT = object()


class PageProbe:
    def __init__(self) -> None:
        self.page_id = "page-1"
        self.context_id = "context-1"
        self.calls: list[str] = []
        self.goto_url: str | None = None
        self.navigation_options: list[tuple[int | None, str, str | None]] = []
        self.url_value = "https://example.test/current"
        self.title_value = "Current title"
        self.html = "<main>ready</main>"
        self.script_value: object = {"ready": True}
        self.script_args: tuple[object, ...] = ()
        self.screenshot_path: Path | None = None
        self.failure_method: str | None = None
        self.failure: Exception | None = None

    def fail(self, method: str, error: Exception) -> None:
        self.failure_method = method
        self.failure = error

    def _failure(self, method: str) -> Exception | None:
        return self.failure if self.failure_method == method else None

    async def navigate(
        self,
        url: str,
        *,
        timeout_ms: int | None = None,
        wait_until: str = "load",
        referer: str | None = None,
    ) -> Result[None, Exception]:
        self.calls.append("navigate")
        self.goto_url = url
        self.navigation_options.append((timeout_ms, wait_until, referer))
        if error := self._failure("navigate"):
            return Error(error)
        return Ok(None)

    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: str = "load",
    ) -> Result[None, Exception]:
        self.calls.append("go_back")
        self.navigation_options.append((timeout_ms, wait_until, None))
        if error := self._failure("go_back"):
            return Error(error)
        return Ok(None)

    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: str = "load",
    ) -> Result[None, Exception]:
        self.calls.append("go_forward")
        self.navigation_options.append((timeout_ms, wait_until, None))
        if error := self._failure("go_forward"):
            return Error(error)
        return Ok(None)

    async def reload(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: str = "load",
    ) -> Result[None, Exception]:
        self.calls.append("reload")
        self.navigation_options.append((timeout_ms, wait_until, None))
        if error := self._failure("reload"):
            return Error(error)
        return Ok(None)

    async def wait_for_navigation(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: str = "load",
    ) -> Result[None, Exception]:
        self.calls.append("wait_for_navigation")
        self.navigation_options.append((timeout_ms, wait_until, None))
        if error := self._failure("wait_for_navigation"):
            return Error(error)
        return Ok(None)

    async def url(self) -> Result[str, Exception]:
        self.calls.append("url")
        if error := self._failure("url"):
            return Error(error)
        return Ok(self.url_value)

    async def title(self) -> Result[str, Exception]:
        self.calls.append("title")
        if error := self._failure("title"):
            return Error(error)
        return Ok(self.title_value)

    async def content(self) -> Result[str, Exception]:
        self.calls.append("content")
        if error := self._failure("content"):
            return Error(error)
        return Ok(self.html)

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]: ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]: ...

    async def screenshot(
        self,
        path: Path | None = None,
    ) -> Result[Path | bytes, Exception]:
        self.calls.append("screenshot")
        self.screenshot_path = path
        if error := self._failure("screenshot"):
            return Error(error)
        return Ok(b"png" if path is None else path)

    async def evaluate(
        self,
        script: str,
        argument: object = _NO_SCRIPT_ARGUMENT,
    ) -> Result[object, Exception]:
        self.calls.append(f"evaluate:{script}")
        self.script_args = () if argument is _NO_SCRIPT_ARGUMENT else (argument,)
        if error := self._failure("evaluate"):
            return Error(error)
        return Ok(self.script_value)


def page_double(probe: PageProbe) -> Page:
    page = MagicMock(spec=Page, wraps=probe)
    return page


@pytest.mark.asyncio
async def test_page_effects_preserve_exact_focus_and_compose() -> None:
    probe = PageProbe()
    page = page_double(probe)
    pipeline = (
        navigate(_, "https://example.test")
        .then(go_back(_))
        .then(go_forward(_))
        .then(reload(_))
        .then(wait_for_navigation(_))
    )

    outcome = await pipeline.run(page)

    assert outcome == Ok(page)
    assert outcome.ok is page
    assert probe.calls == [
        "navigate",
        "go_back",
        "go_forward",
        "reload",
        "wait_for_navigation",
    ]


@pytest.mark.asyncio
async def test_navigate_supports_page_and_url_holes() -> None:
    page_probe = PageProbe()
    page = page_double(page_probe)
    page_hole = await navigate(_, "https://page-hole.test").run(page)

    url_probe = PageProbe()
    captured_page = page_double(url_probe)
    url_hole = await navigate(captured_page, _).run("https://url-hole.test")

    assert page_hole.ok is page
    assert page_probe.goto_url == "https://page-hole.test"
    assert url_hole.ok is captured_page
    assert url_probe.goto_url == "https://url-hole.test"


@pytest.mark.asyncio
async def test_navigate_options_are_keyword_only_and_snapshotted() -> None:
    probe = PageProbe()
    page = page_double(probe)
    options = NavigateOptions(
        timeout=4_000,
        wait_until="networkidle",
        referer="https://referrer.test/source",
    )
    operation = navigate(
        _,
        "https://example.test",
        options=options,
    )
    with pytest.raises(FrozenInstanceError):
        options.timeout = 1
    with pytest.raises(FrozenInstanceError):
        options.wait_until = "load"
    with pytest.raises(FrozenInstanceError):
        options.referer = "https://changed.test"

    outcome = await operation.run(page)

    assert outcome.ok is page
    assert probe.navigation_options[0] == (
        4_000,
        "networkidle",
        "https://referrer.test/source",
    )


@pytest.mark.asyncio
async def test_history_options_are_forwarded_as_immutable_snapshots() -> None:
    options = NavigationOptions(
        timeout=4_000,
        wait_until="networkidle",
    )
    operations = (
        ("go_back", go_back(_, options=options)),
        ("go_forward", go_forward(_, options=options)),
        ("reload", reload(_, options=options)),
        (
            "wait_for_navigation",
            wait_for_navigation(_, options=options),
        ),
    )
    with pytest.raises(FrozenInstanceError):
        options.timeout = 1
    with pytest.raises(FrozenInstanceError):
        options.wait_until = "load"

    for method, operation in operations:
        probe = PageProbe()
        page = page_double(probe)

        outcome = await operation.run(page)

        assert outcome.ok is page
        assert probe.calls == [method]
        assert len(probe.navigation_options) == 1
        assert probe.navigation_options[0] == (4_000, "networkidle", None)


@pytest.mark.asyncio
async def test_history_templates_preserve_exact_browser_error_identity() -> None:
    operations = (
        ("go_back", go_back(_)),
        ("go_forward", go_forward(_)),
        ("reload", reload(_)),
        ("wait_for_navigation", wait_for_navigation(_)),
    )

    for method, operation in operations:
        probe = PageProbe()
        page = page_double(probe)
        browser_error = RuntimeError(f"{method} failed")
        probe.fail(method, browser_error)

        outcome = await operation.run(page)

        assert outcome.is_error()
        assert outcome.error is browser_error
        assert probe.calls == [method]


@pytest.mark.asyncio
async def test_browser_error_identity_survives_without_nested_result() -> None:
    probe = PageProbe()
    page = page_double(probe)
    browser_error = RuntimeError("navigation failed")
    probe.fail("navigate", browser_error)

    outcome = await navigate(_, "https://example.test").then(current_url(_)).run(page)

    assert outcome.is_error()
    assert outcome.error is browser_error
    assert probe.calls == ["navigate"]


@pytest.mark.asyncio
async def test_reader_and_screenshot_templates_return_flat_data(
    tmp_path: Path,
) -> None:
    probe = PageProbe()
    page = page_double(probe)
    first_path = tmp_path / "page-hole.png"
    second_path = tmp_path / "path-hole.png"

    url_outcome = await current_url(_).run(page)
    title_outcome = await title(_).run(page)
    content_outcome = await content(_).run(page)
    bytes_outcome = await screenshot(_).run(page)
    page_hole_outcome = await screenshot_to(_, first_path).run(page)
    path_hole_outcome = await screenshot_to(page, _).run(second_path)

    assert url_outcome == Ok(probe.url_value)
    assert title_outcome == Ok(probe.title_value)
    assert content_outcome == Ok(probe.html)
    assert bytes_outcome == Ok(b"png")
    assert page_hole_outcome == Ok(first_path)
    assert path_hole_outcome == Ok(second_path)


@pytest.mark.asyncio
async def test_title_preserves_the_exact_browser_error() -> None:
    probe = PageProbe()
    page = page_double(probe)
    browser_error = RuntimeError("title read failed")
    probe.fail("title", browser_error)

    outcome = await title(_).run(page)

    assert outcome.is_error()
    assert outcome.error is browser_error


@pytest.mark.asyncio
async def test_evaluate_supports_every_hole_and_exact_browser_call_shape() -> None:
    probe = PageProbe()
    page = page_double(probe)

    page_hole = await evaluate(_, "return true").run(page)
    assert page_hole == Ok(probe.script_value)
    assert probe.script_args == ()

    script_hole = await evaluate(page, _).run("return false")
    assert script_hole == Ok(probe.script_value)
    assert probe.script_args == ()

    with_page_hole = await evaluate_with(_, "value => value", None).run(page)
    assert with_page_hole == Ok(probe.script_value)
    assert probe.script_args == (None,)

    with_script_hole = await evaluate_with(page, _, {"value": 1}).run("value => value")
    assert with_script_hole == Ok(probe.script_value)
    assert probe.script_args == ({"value": 1},)

    with_argument_hole = await evaluate_with(page, "value => value", _).run(None)
    assert with_argument_hole == Ok(probe.script_value)
    assert probe.script_args == (None,)


@pytest.mark.asyncio
async def test_evaluate_with_snapshots_configured_argument() -> None:
    probe = PageProbe()
    page = page_double(probe)
    argument: dict[str, object] = {"value": 1}
    operation = evaluate_with(_, "value => value", argument)
    argument["value"] = 2

    outcome = await operation.run(page)

    assert outcome == Ok(probe.script_value)
    assert probe.script_args == ({"value": 1},)


def test_every_navigation_template_requires_exactly_one_direct_placeholder() -> None:
    page = page_double(PageProbe())
    path = Path("page.png")
    zero_hole_calls = (
        lambda: navigate(page, "https://example.test"),
        lambda: go_back(page),
        lambda: go_forward(page),
        lambda: reload(page),
        lambda: wait_for_navigation(page),
        lambda: current_url(page),
        lambda: title(page),
        lambda: content(page),
        lambda: screenshot(page),
        lambda: screenshot_to(page, path),
        lambda: evaluate(page, "return true"),
        lambda: evaluate_with(page, "value => value", None),
    )
    multiple_hole_calls = (
        lambda: navigate(_, _),
        lambda: screenshot_to(_, _),
        lambda: evaluate(_, _),
        lambda: evaluate_with(_, _, None),
    )

    for construct in zero_hole_calls:
        with pytest.raises(TypeError, match="exactly one direct placeholder"):
            construct()
    for construct in multiple_hole_calls:
        with pytest.raises(TypeError, match="exactly one direct placeholder"):
            construct()


def test_public_exports_and_operation_metadata_match_templates() -> None:
    page = page_double(PageProbe())
    expected_names = [
        "Content",
        "CurrentUrl",
        "Evaluate",
        "EvaluateWith",
        "GoBack",
        "GoForward",
        "NavigateOptions",
        "NavigationOptions",
        "Navigate",
        "Reload",
        "Screenshot",
        "ScreenshotTo",
        "Title",
        "WaitForNavigation",
    ]
    operation_names = [
        content(_).name,
        current_url(_).name,
        evaluate(_, "return true").name,
        evaluate_with(_, "value => value", None).name,
        go_back(_).name,
        go_forward(_).name,
        navigate(_, "https://example.test").name,
        reload(_).name,
        screenshot(_).name,
        screenshot_to(page, _).name,
        title(_).name,
        wait_for_navigation(_).name,
    ]

    assert navigation.__all__ == expected_names
    assert not hasattr(navigation, "navigate")
    assert operation_names == [
        name
        for name in expected_names
        if name not in {"NavigateOptions", "NavigationOptions"}
    ]


@pytest.mark.asyncio
async def test_actual_chromium_supports_every_navigation_template_form(
    tmp_path: Path,
) -> None:
    async with BrowserSession(
        options=BrowserOptions(headless=True, timeout=10_000)
    ) as session:
        context = session.context
        page = session.page

        first_url = "data:text/html," + quote("<title>First</title><main>first</main>")
        second_url = "data:text/html," + quote(
            "<title>Second</title><main>second</main>"
        )
        third_url = "data:text/html," + quote("<title>Third</title><main>third</main>")
        first_navigation = await navigate(_, first_url).run(page)
        second_navigation = await navigate(page, _).run(second_url)
        assert first_navigation.ok is page
        assert second_navigation.ok is page

        history_options = NavigationOptions(
            timeout=10_000,
            wait_until="domcontentloaded",
        )
        assert (await go_back(_, options=history_options).run(page)).ok is page
        assert (await current_url(_).run(page)).ok == first_url
        assert (await go_forward(_, options=history_options).run(page)).ok is page
        assert (await current_url(_).run(page)).ok == second_url
        assert (await title(_).run(page)).ok == "Second"
        assert (await reload(_, options=history_options).run(page)).ok is page

        async def navigate_later() -> None:
            await asyncio.sleep(0.1)
            assert (await navigate(_, third_url).run(page)).is_ok()

        trigger = asyncio.create_task(navigate_later())
        assert (
            await wait_for_navigation(_, options=history_options).run(page)
        ).ok is page
        await trigger
        assert (await current_url(_).run(page)).ok == third_url

        assert "third" in (await content(_).run(page)).ok
        assert (await screenshot(_).run(page)).ok

        page_path = tmp_path / "actual-page-hole.png"
        path_path = tmp_path / "actual-path-hole.png"
        assert (await screenshot_to(_, page_path).run(page)).ok == page_path
        assert (await screenshot_to(page, _).run(path_path)).ok == path_path

        assert (await evaluate(_, "() => document.title").run(page)).ok == "Third"
        assert (await evaluate(page, _).run("() => document.title")).ok == "Third"
        assert (await evaluate(page, _).run("value => value")).ok is None
        assert (await evaluate_with(_, "value => value", None).run(page)).ok is None
        assert (
            await evaluate_with(page, _, {"answer": 42}).run("value => value.answer")
        ).ok == 42
        assert (
            await evaluate_with(page, "value => value.answer", _).run({"answer": 43})
        ).ok == 43

        option_page_outcome = await context.new_page()
        assert option_page_outcome.is_ok(), option_page_outcome
        option_page = option_page_outcome.ok
        assert (await navigate(_, first_url).run(option_page)).is_ok()
        assert (await navigate(_, second_url).run(option_page)).is_ok()

        with pytest.raises(ValueError, match="timeout must be non-negative"):
            NavigationOptions(
                timeout=-1,
                wait_until="domcontentloaded",
            )
        assert (await option_page.close()).is_ok()
