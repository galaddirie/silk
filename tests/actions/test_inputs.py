"""Behavioral contracts for the public input-action seam."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import Error, Ok, Result, _

import silk.actions.input as input_actions
from silk.actions.input import (
    ClickOptions,
    DoubleClickOptions,
    DragOptions,
    FillOptions,
    TypeTextOptions,
    Click as click,
    DoubleClick as double_click,
    Drag as drag,
    Fill as fill,
    KeyDown as key_down,
    KeyPress as key_press,
    KeyUp as key_up,
    MouseDown as mouse_down,
    MouseMove as mouse_move,
    MouseMoveTo as mouse_move_to,
    MouseUp as mouse_up,
    ScrollIntoView as scroll_into_view,
    ScrollTo as scroll_to,
    SelectText as select_text,
    SelectValue as select_value,
    TypeText as type_text,
)
from silk.browsers.models import ElementHandle, KeyModifier, MouseButtonLiteral, Page


class ProbeElement(ElementHandle):
    def __init__(
        self,
        *,
        page_id: str = "page",
        selector: str = "#element",
    ) -> None:
        self._page_id = page_id
        self._context_id = "context"
        self._selector: str | None = selector
        self.effects: dict[str, Result[None, Exception]] = {}
        self.calls: list[tuple[str, object]] = []

    @property
    def page_id(self) -> str:
        return self._page_id

    @property
    def context_id(self) -> str:
        return self._context_id

    @property
    def selector(self) -> str | None:
        return self._selector

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        self.calls.append(("query_selector", selector))
        return Ok(None)

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        self.calls.append(("query_selector_all", selector))
        return Ok([])

    async def click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        click_count: int = 1,
        force: bool = False,
    ) -> Result[None, Exception]:
        self.calls.append(
            (
                "click",
                (timeout_ms, button, modifiers, delay_ms, click_count, force),
            )
        )
        return self.effects.get("click", Ok(None))

    async def double_click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        force: bool = False,
    ) -> Result[None, Exception]:
        self.calls.append(
            (
                "double_click",
                (timeout_ms, button, modifiers, delay_ms, force),
            )
        )
        return self.effects.get("double_click", Ok(None))

    async def fill(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear: bool = False,
    ) -> Result[None, Exception]:
        self.calls.append(("fill", (text, timeout_ms, clear)))
        return self.effects.get("fill", Ok(None))

    async def type(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        self.calls.append(("type", (text, timeout_ms, delay_ms)))
        return self.effects.get("type", Ok(None))

    async def select(
        self,
        *,
        value: str | None = None,
        text: str | None = None,
    ) -> Result[None, Exception]:
        self.calls.append(("select", (value, text)))
        return self.effects.get("select", Ok(None))

    async def scroll_into_view(self) -> Result[None, Exception]:
        self.calls.append(("scroll_into_view", None))
        return self.effects.get("scroll_into_view", Ok(None))

    async def text(self) -> Result[str, Exception]:
        return Ok("text")

    async def inner_text(self) -> Result[str, Exception]:
        return Ok("inner")

    async def html(self, *, outer: bool = True) -> Result[str, Exception]:
        return Ok("<div></div>" if outer else "")

    async def attribute(
        self,
        name: str,
    ) -> Result[str | None, Exception]:
        return Ok(None)

    async def move_pointer_to(
        self,
        *,
        offset: tuple[int, int] = (0, 0),
        center: bool = True,
        steps: int = 1,
    ) -> Result[None, Exception]:
        self.calls.append(("move_pointer_to", (offset, center, steps)))
        return self.effects.get("move_pointer_to", Ok(None))

    async def drag_to(
        self,
        target: ElementHandle,
        *,
        steps: int = 1,
        move_to_center: bool = True,
        position_offset: tuple[int, int] | None = None,
        source_offset: tuple[int, int] | None = None,
        target_offset: tuple[int, int] | None = None,
    ) -> Result[None, Exception]:
        self.calls.append(
            (
                "drag_to",
                (
                    target,
                    steps,
                    move_to_center,
                    position_offset,
                    source_offset,
                    target_offset,
                ),
            )
        )
        return self.effects.get("drag_to", Ok(None))


def page_double() -> MagicMock:
    page = MagicMock(spec=Page)
    page.page_id = "page"
    page.context_id = "context"
    page.mouse_move = AsyncMock(return_value=Ok(None))
    page.mouse_down = AsyncMock(return_value=Ok(None))
    page.mouse_up = AsyncMock(return_value=Ok(None))
    page.key_press = AsyncMock(return_value=Ok(None))
    page.key_down = AsyncMock(return_value=Ok(None))
    page.key_up = AsyncMock(return_value=Ok(None))
    page.scroll = AsyncMock(return_value=Ok(None))
    return page


def test_public_input_surface_uses_pascal_case_action_names() -> None:
    expected = {
        "Click",
        "ClickOptions",
        "DoubleClick",
        "DoubleClickOptions",
        "Drag",
        "DragOptions",
        "Fill",
        "FillOptions",
        "InputPage",
        "KeyDown",
        "KeyPress",
        "KeyUp",
        "MouseDown",
        "MouseMove",
        "MouseMoveTo",
        "MouseUp",
        "ScrollIntoView",
        "ScrollTo",
        "SelectText",
        "SelectValue",
        "TypeText",
        "TypeTextOptions",
    }

    assert set(input_actions.__all__) == expected
    assert all(name[0].isupper() for name in input_actions.__all__)
    assert not hasattr(input_actions, "type_text")
    assert input_actions.Click is click
    assert input_actions.TypeText is type_text
    assert type_text("#field", "value", _).name == "TypeText"


@pytest.mark.asyncio
async def test_element_input_actions_translate_configuration_and_retain_focus() -> None:
    element = ProbeElement()

    clicked = await click(
        _,
        element,
        options=ClickOptions(
            timeout_ms=500,
            button="right",
            modifiers=(KeyModifier.ALT,),
            delay_ms=7,
            click_count=3,
            force=True,
        ),
    ).run(element)
    doubled = await double_click(
        element,
        _,
        options=DoubleClickOptions(timeout_ms=600, button="middle"),
    ).run(element)
    filled = await fill(
        element,
        _,
        element,
        options=FillOptions(timeout_ms=700, clear=True),
    ).run("replacement")
    typed = await type_text(
        element,
        "more",
        _,
        options=TypeTextOptions(timeout_ms=800, delay_ms=9),
    ).run(element)

    assert clicked.ok is element
    assert doubled.ok is element
    assert filled.ok is element
    assert typed.ok is element
    assert ("click", (500, "right", (KeyModifier.ALT,), 7, 3, True)) in element.calls
    assert ("double_click", (600, "middle", (), None, False)) in element.calls
    assert ("fill", ("replacement", 700, True)) in element.calls
    assert ("type", ("more", 800, 9)) in element.calls


@pytest.mark.asyncio
async def test_selection_empty_values_scroll_and_error_identity_are_truthful() -> None:
    element = ProbeElement()

    value = await select_value(_, "", element).run(element)
    label = await select_text(element, _, element).run("")
    scrolled = await scroll_into_view(_, element).run(element)

    assert value.ok is element
    assert label.ok is element
    assert scrolled.ok is element
    assert ("select", ("", None)) in element.calls
    assert ("select", (None, "")) in element.calls

    browser_error = RuntimeError("native click failed")
    element.effects["click"] = Error(browser_error)
    failed = await click(_, element).run(element)
    assert failed.is_error()
    assert failed.error is browser_error


@pytest.mark.asyncio
async def test_mouse_move_to_is_semantic_and_never_needs_a_driver() -> None:
    element = ProbeElement()

    outcome = await mouse_move_to(
        _,
        element,
        offset=(2, 3),
        center=True,
        steps=4,
    ).run(element)

    assert outcome.ok is element
    assert ("move_pointer_to", ((2, 3), True, 4)) in element.calls
    assert not hasattr(element, "driver")

    browser_error = RuntimeError("pointer move failed")
    element.effects["move_pointer_to"] = Error(browser_error)
    failed = await mouse_move_to(element, _).run(element)
    assert failed.error is browser_error


@pytest.mark.asyncio
async def test_drag_supports_both_holes_and_forwards_semantic_options() -> None:
    source = ProbeElement(selector="#source")
    target = ProbeElement(selector="#target")
    options = DragOptions(
        steps=6,
        move_to_center=True,
        position_offset=(1, 2),
        source_offset=(3, 4),
        target_offset=(5, 6),
    )

    source_hole = await drag(_, target, options=options).run(source)
    target_hole = await drag(source, _, options=options).run(target)

    assert source_hole.ok is source
    assert target_hole.ok is source
    expected_call = (
        "drag_to",
        (target, 6, True, (1, 2), (3, 4), (5, 6)),
    )
    assert source.calls.count(expected_call) == 2


@pytest.mark.asyncio
async def test_drag_preserves_original_semantic_adapter_error() -> None:
    source = ProbeElement()
    target = ProbeElement()
    adapter_error = RuntimeError("drag failed")
    source.effects["drag_to"] = Error(adapter_error)

    failed = await drag(_, target).run(source)

    assert failed.error is adapter_error


@pytest.mark.asyncio
async def test_page_input_actions_translate_primitives_and_retain_exact_page() -> None:
    page = page_double()

    moved = await mouse_move(_, page, steps=3).run((12, 34))
    down = await mouse_down(_, button="right").run(page)
    up = await mouse_up(_, button="middle").run(page)
    pressed = await key_press(_, page, delay_ms=5).run("Enter")
    held = await key_down("Shift", _).run(page)
    released = await key_up(_, page).run("Shift")
    scrolled = await scroll_to(_, page).run((50, 60))

    assert all(
        result.ok is page
        for result in (moved, down, up, pressed, held, released, scrolled)
    )
    page.mouse_move.assert_awaited_once_with(12, 34, steps=3)
    page.mouse_down.assert_awaited_once_with(button="right")
    page.mouse_up.assert_awaited_once_with(button="middle")
    page.key_press.assert_awaited_once_with("Enter", delay_ms=5)
    page.key_down.assert_awaited_once_with("Shift")
    page.key_up.assert_awaited_once_with("Shift")
    page.scroll.assert_awaited_once_with(x=50, y=60)


@pytest.mark.asyncio
async def test_every_supported_input_operand_position_executes() -> None:
    element = ProbeElement()
    page = page_double()

    element_results = [
        await click(_, element).run(element),
        await click(element, _).run(element),
        await double_click(_, element).run(element),
        await double_click(element, _).run(element),
        await fill(_, "value", element).run(element),
        await fill(element, _, element).run("value"),
        await fill(element, "value", _).run(element),
        await type_text(_, "value", element).run(element),
        await type_text(element, _, element).run("value"),
        await type_text(element, "value", _).run(element),
        await select_value(_, "one", element).run(element),
        await select_value(element, _, element).run("one"),
        await select_value(element, "one", _).run(element),
        await select_text(_, "One", element).run(element),
        await select_text(element, _, element).run("One"),
        await select_text(element, "One", _).run(element),
        await scroll_into_view(_, element).run(element),
        await scroll_into_view(element, _).run(element),
        await mouse_move_to(_, element).run(element),
        await mouse_move_to(element, _).run(element),
        await drag(_, element).run(element),
        await drag(element, _).run(element),
    ]
    assert all(result.is_ok() for result in element_results)

    page_results = [
        await mouse_move(_, page).run((1, 2)),
        await mouse_move((1, 2), _).run(page),
        await mouse_down(_).run(page),
        await mouse_up(_).run(page),
        await key_press(_, page).run("Enter"),
        await key_press("Enter", _).run(page),
        await key_down(_, page).run("Shift"),
        await key_down("Shift", _).run(page),
        await key_up(_, page).run("Shift"),
        await key_up("Shift", _).run(page),
        await scroll_to(_, page).run((3, 4)),
        await scroll_to((3, 4), _).run(page),
    ]
    assert all(result.is_ok() for result in page_results)


def test_every_input_template_requires_exactly_one_direct_placeholder() -> None:
    element = ProbeElement()
    page = page_double()
    zero_hole_calls = (
        lambda: drag(element, element),
        lambda: click(element, element),
        lambda: double_click(element, element),
        lambda: fill(element, "value", element),
        lambda: type_text(element, "value", element),
        lambda: select_value(element, "one", element),
        lambda: select_text(element, "One", element),
        lambda: scroll_into_view(element, element),
        lambda: mouse_move((1, 2), page),
        lambda: mouse_move_to(element, element),
        lambda: mouse_down(page),
        lambda: mouse_up(page),
        lambda: key_press("Enter", page),
        lambda: key_down("Shift", page),
        lambda: key_up("Shift", page),
        lambda: scroll_to((1, 2), page),
    )
    multiple_hole_calls = (
        lambda: drag(_, _),
        lambda: click(_, _),
        lambda: double_click(_, _),
        lambda: fill(_, _, element),
        lambda: type_text(_, _, element),
        lambda: select_value(_, _, element),
        lambda: select_text(_, _, element),
        lambda: scroll_into_view(_, _),
        lambda: mouse_move(_, _),
        lambda: mouse_move_to(_, _),
        lambda: key_press(_, _),
        lambda: key_down(_, _),
        lambda: key_up(_, _),
        lambda: scroll_to(_, _),
    )

    for construct in (*zero_hole_calls, *multiple_hole_calls):
        with pytest.raises(TypeError, match="exactly one direct placeholder"):
            construct()


def test_input_configuration_is_frozen_and_rejects_invalid_values() -> None:
    drag_options = DragOptions(
        steps=2,
        position_offset=(1, 2),
        source_offset=(3, 4),
        target_offset=(5, 6),
    )
    with pytest.raises(FrozenInstanceError):
        drag_options.steps = 3

    invalid = (
        lambda: DragOptions(steps=0),
        lambda: ClickOptions(click_count=0),
        lambda: ClickOptions(timeout_ms=-1),
        lambda: ClickOptions(modifiers=(KeyModifier.NONE,)),
        lambda: ClickOptions(modifiers=(KeyModifier.ALT, KeyModifier.ALT)),
        lambda: DoubleClickOptions(delay_ms=-1),
        lambda: TypeTextOptions(delay_ms=-1),
        lambda: FillOptions(timeout_ms=-1),
    )
    for construct in invalid:
        with pytest.raises(ValueError):
            construct()


def test_input_templates_do_not_grow_runtime_binding_shortcuts() -> None:
    for template in (
        click,
        double_click,
        drag,
        fill,
        key_down,
        key_press,
        key_up,
        mouse_down,
        mouse_move,
        mouse_move_to,
        mouse_up,
        scroll_into_view,
        scroll_to,
        select_text,
        select_value,
        type_text,
    ):
        assert not hasattr(template, "execute")
        assert not hasattr(template, "bind")
