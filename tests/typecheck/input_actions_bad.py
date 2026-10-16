# pyright: strict
"""Calls that strict type checkers must reject for input-action templates."""

from fp_ops import _

from silk.actions.elements import Element, ElementScope, ElementTarget
from silk.actions.input import (
    ClickOptions,
    DoubleClickOptions,
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
from silk.browsers.models import KeyModifier, Page


def zero_hole_calls(
    source: Element,
    target: Element,
    element_target: ElementTarget,
    scope: ElementScope,
    page: Page,
) -> None:
    # typecheck-case: input_actions.001
    drag(source, target)
    # typecheck-case: input_actions.002
    click(element_target, scope)
    # typecheck-case: input_actions.003
    double_click(element_target, scope)
    # typecheck-case: input_actions.004
    fill(element_target, "value", scope)
    # typecheck-case: input_actions.005
    type_text(element_target, "value", scope)
    # typecheck-case: input_actions.006
    select_value(element_target, "value", scope)
    # typecheck-case: input_actions.007
    select_text(element_target, "Value", scope)
    # typecheck-case: input_actions.008
    scroll_into_view(element_target, scope)
    # typecheck-case: input_actions.009
    mouse_move((1, 2), page)
    # typecheck-case: input_actions.010
    mouse_move_to(element_target, scope)
    # typecheck-case: input_actions.011
    mouse_down(page)
    # typecheck-case: input_actions.012
    mouse_up(page)
    # typecheck-case: input_actions.013
    key_press("Enter", page)
    # typecheck-case: input_actions.014
    key_down("Shift", page)
    # typecheck-case: input_actions.015
    key_up("Shift", page)
    # typecheck-case: input_actions.016
    scroll_to((1, 2), page)


def two_hole_calls(scope: ElementScope) -> None:
    # typecheck-case: input_actions.017
    drag(_, _)
    # typecheck-case: input_actions.018
    click(_, _)
    # typecheck-case: input_actions.019
    double_click(_, _)
    # typecheck-case: input_actions.020
    fill(_, _, scope)
    # typecheck-case: input_actions.021
    type_text(_, _, scope)
    # typecheck-case: input_actions.022
    select_value(_, _, scope)
    # typecheck-case: input_actions.023
    select_text(_, _, scope)
    # typecheck-case: input_actions.024
    scroll_into_view(_, _)
    # typecheck-case: input_actions.025
    mouse_move(_, _)
    # typecheck-case: input_actions.026
    mouse_move_to(_, _)
    # typecheck-case: input_actions.027
    key_press(_, _)
    # typecheck-case: input_actions.028
    key_down(_, _)
    # typecheck-case: input_actions.029
    key_up(_, _)
    # typecheck-case: input_actions.030
    scroll_to(_, _)


def wrong_operand_and_configuration_types(
    source: Element,
    element_target: ElementTarget,
) -> None:
    # typecheck-case: input_actions.031
    drag("#source", _)
    # typecheck-case: input_actions.032
    drag(source, _, options="not options")
    # typecheck-case: input_actions.033
    click(element_target, _, options="not options")
    # typecheck-case: input_actions.034
    double_click(element_target, _, options="not options")
    # typecheck-case: input_actions.035
    fill(1, "value", _)
    # typecheck-case: input_actions.036
    fill(element_target, 1, _)
    # typecheck-case: input_actions.037
    fill(element_target, "value", _, options="not options")
    # typecheck-case: input_actions.038
    type_text(element_target, "value", _, options="not options")
    # typecheck-case: input_actions.039
    mouse_move("1,2", _)
    # typecheck-case: input_actions.040
    mouse_move((1, 2), _, steps="many")
    # typecheck-case: input_actions.041
    mouse_move_to(element_target, _, offset="1,2")
    # typecheck-case: input_actions.042
    mouse_down(_, button="invalid")
    # typecheck-case: input_actions.043
    mouse_down(_, options="removed")
    # typecheck-case: input_actions.044
    key_press(1, _)
    # typecheck-case: input_actions.045
    key_press("Enter", _, options="removed")
    # typecheck-case: input_actions.046
    key_down("Shift", _, delay_ms=1)
    # typecheck-case: input_actions.047
    scroll_to((1.0, 2.0), _)
    # typecheck-case: input_actions.048
    ClickOptions(button="invalid")
    # typecheck-case: input_actions.049
    ClickOptions(modifiers=("shift",))
    # typecheck-case: input_actions.050
    ClickOptions(modifiers=[KeyModifier.SHIFT])
    # typecheck-case: input_actions.051
    DoubleClickOptions(force="yes")
    # typecheck-case: input_actions.052
    FillOptions(clear="yes")
    # typecheck-case: input_actions.053
    TypeTextOptions(delay_ms="slow")


async def invalid_pipeline_input(
    target: Element,
    page: Page,
) -> None:
    # typecheck-case: input_actions.054
    await drag(_, target).run("not an element")
    # typecheck-case: input_actions.055
    await mouse_move((1, 2), _).run("not a page")
    # typecheck-case: input_actions.056
    await fill(_, "value", target).run(42)
    # typecheck-case: input_actions.057
    await key_press(_, page).run(42)
    # typecheck-case: input_actions.058
    await mouse_move_to(_, target).run(42)
