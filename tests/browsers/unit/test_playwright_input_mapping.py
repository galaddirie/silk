"""Playwright translation contracts exercised through public input actions."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fp_ops import _
from playwright.async_api import (
    Browser,
    BrowserContext as PWBrowserContext,
    ElementHandle as PWElementHandle,
    Mouse as PWMouse,
    Page as PWPage,
)

from silk.actions.input import (
    Click as click,
    ClickOptions,
    DoubleClick as double_click,
    DoubleClickOptions,
    Drag as drag,
    DragOptions,
    Fill as fill,
    FillOptions,
    TypeText as type_text,
    TypeTextOptions,
)
from silk.browsers.drivers.playwright import PlaywrightBrowser
from silk.browsers.models import ElementHandle, KeyModifier, Page
from silk.errors import DragElementMismatchError


async def public_element() -> tuple[Page, ElementHandle, MagicMock]:
    browser = MagicMock(spec=Browser)
    context = MagicMock(spec=PWBrowserContext)
    page = MagicMock(spec=PWPage)
    element = MagicMock(spec=PWElementHandle)
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=page)
    context.pages = [page]
    page.query_selector = AsyncMock(return_value=element)
    element.click = AsyncMock(return_value=None)
    element.dblclick = AsyncMock(return_value=None)
    element.fill = AsyncMock(return_value=None)
    element.type = AsyncMock(return_value=None)
    driver = PlaywrightBrowser(MagicMock(), browser)

    context_result = await driver.new_context()
    assert context_result.is_ok()
    page_result = await context_result.ok.new_page()
    assert page_result.is_ok()
    element_result = await page_result.ok.query_selector("#field")
    assert element_result.is_ok() and element_result.ok is not None
    return page_result.ok, element_result.ok, element


async def public_drag_elements() -> tuple[
    ElementHandle,
    ElementHandle,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    browser = MagicMock(spec=Browser)
    context = MagicMock(spec=PWBrowserContext)
    page = MagicMock(spec=PWPage)
    mouse = MagicMock(spec=PWMouse)
    source_native = MagicMock(spec=PWElementHandle)
    target_native = MagicMock(spec=PWElementHandle)
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=page)
    context.pages = [page]
    page.mouse = mouse
    page.query_selector = AsyncMock(side_effect=[source_native, target_native])
    source_native.bounding_box = AsyncMock(
        return_value={"x": 10.0, "y": 20.0, "width": 20.0, "height": 10.0}
    )
    target_native.bounding_box = AsyncMock(
        return_value={"x": 100.0, "y": 200.0, "width": 40.0, "height": 20.0}
    )
    mouse.move = AsyncMock(return_value=None)
    mouse.down = AsyncMock(return_value=None)
    mouse.up = AsyncMock(return_value=None)
    driver = PlaywrightBrowser(MagicMock(), browser)

    context_result = await driver.new_context()
    assert context_result.is_ok()
    page_result = await context_result.ok.new_page()
    assert page_result.is_ok()
    source_result = await page_result.ok.query_selector("#source")
    target_result = await page_result.ok.query_selector("#target")
    assert source_result.is_ok() and source_result.ok is not None
    assert target_result.is_ok() and target_result.ok is not None
    return (
        source_result.ok,
        target_result.ok,
        mouse,
        source_native,
        target_native,
    )


@pytest.mark.asyncio
async def test_public_click_and_double_click_map_every_native_option() -> None:
    page, element, native = await public_element()

    clicked = await click(
        _,
        page,
        options=ClickOptions(
            timeout_ms=321,
            button="right",
            modifiers=(KeyModifier.ALT, KeyModifier.COMMAND),
            delay_ms=12,
            click_count=3,
            force=True,
        ),
    ).run(element)
    doubled = await double_click(
        element,
        _,
        options=DoubleClickOptions(
            timeout_ms=654,
            button="middle",
            modifiers=(KeyModifier.CTRL, KeyModifier.SHIFT),
            delay_ms=23,
            force=True,
        ),
    ).run(page)

    assert clicked.ok is element
    assert doubled.ok is element
    native.click.assert_awaited_once_with(
        button="right",
        click_count=3,
        delay=12,
        timeout=321,
        force=True,
        modifiers=["Alt", "Meta"],
    )
    native.dblclick.assert_awaited_once_with(
        button="middle",
        delay=23,
        timeout=654,
        force=True,
        modifiers=["Control", "Shift"],
    )


@pytest.mark.asyncio
async def test_public_fill_and_type_map_clear_timeout_and_delay() -> None:
    page, element, native = await public_element()

    filled = await fill(
        _,
        "replacement",
        page,
        options=FillOptions(timeout_ms=111, clear=True),
    ).run(element)
    typed = await type_text(
        element,
        _,
        page,
        options=TypeTextOptions(timeout_ms=222, delay_ms=9),
    ).run("append")

    assert filled.ok is element
    assert typed.ok is element
    assert native.fill.await_args_list == [
        call("", timeout=111),
        call("replacement", timeout=111),
    ]
    native.type.assert_awaited_once_with("append", delay=9, timeout=222)


@pytest.mark.asyncio
async def test_native_input_exception_survives_public_action_unchanged() -> None:
    page, element, native = await public_element()
    native_error = RuntimeError("element detached")
    native.click.side_effect = native_error

    outcome = await click(_, page).run(element)

    assert outcome.is_error()
    assert outcome.error is native_error


@pytest.mark.asyncio
async def test_drag_does_not_release_when_initial_source_move_fails() -> None:
    source, target, mouse, _source_native, _target_native = await public_drag_elements()
    primary = RuntimeError("source move failed")
    mouse.move.side_effect = primary

    outcome = await drag(_, target).run(source)

    assert outcome.is_error()
    assert outcome.error is primary
    mouse.down.assert_not_awaited()
    mouse.up.assert_not_awaited()


@pytest.mark.asyncio
async def test_drag_releases_mouse_and_preserves_down_failure() -> None:
    source, target, mouse, _source_native, _target_native = await public_drag_elements()
    primary = RuntimeError("mouse down failed after press")
    mouse.down.side_effect = primary

    outcome = await drag(_, target).run(source)

    assert outcome.is_error()
    assert outcome.error is primary
    mouse.down.assert_awaited_once_with()
    mouse.up.assert_awaited_once_with()
    assert mouse.move.await_count == 1


@pytest.mark.asyncio
async def test_drag_releases_mouse_and_preserves_target_move_failure() -> None:
    source, target, mouse, _source_native, _target_native = await public_drag_elements()
    primary = RuntimeError("target move failed")
    mouse.move.side_effect = [None, primary]

    outcome = await drag(_, target, options=DragOptions(steps=7)).run(source)

    assert outcome.is_error()
    assert outcome.error is primary
    mouse.down.assert_awaited_once_with()
    mouse.up.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_drag_preserves_exact_target_move_cancellation() -> None:
    source, target, mouse, _source_native, _target_native = await public_drag_elements()
    primary = asyncio.CancelledError("target move cancelled")
    mouse.move.side_effect = [None, primary]

    with pytest.raises(asyncio.CancelledError) as caught:
        await drag(_, target).run(source)

    assert caught.value is primary
    mouse.up.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_drag_maps_coordinates_and_releases_after_success() -> None:
    source, target, mouse, source_native, target_native = await public_drag_elements()

    outcome = await drag(
        _,
        target,
        options=DragOptions(
            steps=7,
            position_offset=(1, 2),
            source_offset=(3, 4),
            target_offset=(5, 6),
        ),
    ).run(source)

    assert outcome.is_ok()
    assert outcome.ok is source
    source_native.bounding_box.assert_awaited_once_with()
    target_native.bounding_box.assert_awaited_once_with()
    assert mouse.move.await_args_list == [
        call(24, 31),
        call(126, 218, steps=7),
    ]
    mouse.down.assert_awaited_once_with()
    mouse.up.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_drag_preserves_bounding_box_failure() -> None:
    source, target, mouse, source_native, _target_native = await public_drag_elements()
    primary = RuntimeError("bounding box failed")
    source_native.bounding_box.side_effect = primary

    outcome = await drag(_, target).run(source)

    assert outcome.is_error()
    assert outcome.error is primary
    mouse.move.assert_not_awaited()
    mouse.down.assert_not_awaited()
    mouse.up.assert_not_awaited()


@pytest.mark.asyncio
async def test_drag_rejects_elements_on_different_pages() -> None:
    source, _target, _mouse, source_native, _target_native = (
        await public_drag_elements()
    )
    _other_source, other_target, _other_mouse, _other_native, _other_target = (
        await public_drag_elements()
    )

    outcome = await drag(_, other_target).run(source)

    assert outcome.is_error()
    error = outcome.error
    assert isinstance(error, DragElementMismatchError)
    assert error.source_page_id == source.page_id
    assert error.target_page_id == other_target.page_id
    source_native.bounding_box.assert_not_awaited()
