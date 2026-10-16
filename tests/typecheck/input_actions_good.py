# pyright: strict
"""Positive typing contracts for public input-action templates."""

from typing import assert_type

from fp_ops import Operation, Result, _

from silk.actions.elements import Element, ElementScope, ElementTarget
from silk.actions.input import (
    ClickOptions,
    DoubleClickOptions,
    DragOptions,
    FillOptions,
    InputPage,
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
from silk.browsers.drivers.playwright import (
    PlaywrightElementHandle,
    PlaywrightPage,
)
from silk.browsers.models import (
    CoordinateType,
    KeyModifier,
)


def every_element_operand_position(
    target: ElementTarget,
    scope: ElementScope,
    element: Element,
) -> None:
    assert_type(click(_, scope), Operation[ElementTarget, Element])
    assert_type(click(target, _), Operation[ElementScope, Element])
    assert_type(
        click(
            _,
            scope,
            options=ClickOptions(
                button="right",
                modifiers=(KeyModifier.SHIFT,),
                click_count=2,
            ),
        ),
        Operation[ElementTarget, Element],
    )
    assert_type(double_click(_, scope), Operation[ElementTarget, Element])
    assert_type(double_click(target, _), Operation[ElementScope, Element])
    assert_type(
        double_click(_, scope, options=DoubleClickOptions(force=True)),
        Operation[ElementTarget, Element],
    )

    assert_type(fill(_, "value", scope), Operation[ElementTarget, Element])
    assert_type(fill(target, _, scope), Operation[str, Element])
    assert_type(fill(target, "value", _), Operation[ElementScope, Element])
    assert_type(
        fill(_, "value", scope, options=FillOptions(clear=True)),
        Operation[ElementTarget, Element],
    )
    assert_type(type_text(_, "value", scope), Operation[ElementTarget, Element])
    assert_type(type_text(target, _, scope), Operation[str, Element])
    assert_type(type_text(target, "value", _), Operation[ElementScope, Element])
    assert_type(
        type_text(
            _,
            "value",
            scope,
            options=TypeTextOptions(delay_ms=5),
        ),
        Operation[ElementTarget, Element],
    )

    assert_type(select_value(_, "one", scope), Operation[ElementTarget, Element])
    assert_type(select_value(target, _, scope), Operation[str, Element])
    assert_type(select_value(target, "one", _), Operation[ElementScope, Element])
    assert_type(select_text(_, "One", scope), Operation[ElementTarget, Element])
    assert_type(select_text(target, _, scope), Operation[str, Element])
    assert_type(select_text(target, "One", _), Operation[ElementScope, Element])

    assert_type(scroll_into_view(_, scope), Operation[ElementTarget, Element])
    assert_type(scroll_into_view(target, _), Operation[ElementScope, Element])
    assert_type(mouse_move_to(_, scope), Operation[ElementTarget, Element])
    assert_type(mouse_move_to(target, _), Operation[ElementScope, Element])

    assert_type(drag(_, element), Operation[Element, Element])
    assert_type(drag(element, _), Operation[Element, Element])
    assert_type(
        drag(_, element, options=DragOptions(source_offset=(1, 2))),
        Operation[Element, Element],
    )


def every_page_operand_position(
    position: CoordinateType,
    page: InputPage,
) -> None:
    assert_type(mouse_move(_, page), Operation[CoordinateType, InputPage])
    assert_type(mouse_move(position, _), Operation[InputPage, InputPage])
    assert_type(
        mouse_move(_, page, steps=3),
        Operation[CoordinateType, InputPage],
    )
    assert_type(mouse_down(_), Operation[InputPage, InputPage])
    assert_type(
        mouse_up(_, button="right"),
        Operation[InputPage, InputPage],
    )

    assert_type(key_press(_, page), Operation[str, InputPage])
    assert_type(key_press("Enter", _), Operation[InputPage, InputPage])
    assert_type(
        key_press(_, page, delay_ms=5),
        Operation[str, InputPage],
    )
    assert_type(key_down(_, page), Operation[str, InputPage])
    assert_type(key_down("Shift", _), Operation[InputPage, InputPage])
    assert_type(key_up(_, page), Operation[str, InputPage])
    assert_type(key_up("Shift", _), Operation[InputPage, InputPage])
    assert_type(scroll_to(_, page), Operation[CoordinateType, InputPage])
    assert_type(scroll_to(position, _), Operation[InputPage, InputPage])


async def concrete_playwright_types_are_valid(
    page: PlaywrightPage,
    source: PlaywrightElementHandle,
    target: PlaywrightElementHandle,
) -> None:
    dragged = await drag(_, target).run(source)
    dragged_other_position = await drag(source, _).run(target)
    moved = await mouse_move((10, 20), _).run(page)
    filled = await fill(source, "hello", _).run(page)
    hovered = await mouse_move_to(source, _).run(page)

    assert_type(dragged, Result[Element, Exception])
    assert_type(dragged_other_position, Result[Element, Exception])
    assert_type(moved, Result[InputPage, Exception])
    assert_type(filled, Result[Element, Exception])
    assert_type(hovered, Result[Element, Exception])
