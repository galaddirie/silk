"""Typed input actions with explicit element and page focus.

Every public symbol is a construction-time FP-Ops template.  A caller chooses
one semantic positional operand as the unary pipeline input by placing ``_``
there; all other operands are snapshotted when the operation is constructed.

Coordinate clicks are intentionally not synthesized from move/down/up calls:
that sequence cannot provide atomic browser click semantics or safely recover
from a partial failure. Use :func:`Click` with an element target instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from fp_ops import Error, Ok, Result, result_operation_template

from silk.actions._scope import (
    Element,
    ElementScope,
    ElementTarget,
    require_target,
)
from silk.browsers.models import (
    CoordinateType,
    KeyModifier,
    MouseButtonLiteral,
    Page,
)

InputPage = Page


def _require_non_negative(**values: int | None) -> None:
    for name, value in values.items():
        if value is not None and value < 0:
            raise ValueError(f"{name} must be non-negative")


def _require_distinct_active_modifiers(modifiers: tuple[KeyModifier, ...]) -> None:
    if KeyModifier.NONE in modifiers:
        raise ValueError("KeyModifier.NONE is not an active modifier")
    if len(set(modifiers)) != len(modifiers):
        raise ValueError("modifiers must not contain duplicates")


@dataclass(frozen=True, slots=True)
class ClickOptions:
    """Configuration for a native element click."""

    timeout_ms: int | None = None
    button: MouseButtonLiteral = "left"
    modifiers: tuple[KeyModifier, ...] = ()
    delay_ms: int | None = None
    click_count: int = 1
    force: bool = False

    def __post_init__(self) -> None:
        _require_non_negative(timeout_ms=self.timeout_ms, delay_ms=self.delay_ms)
        _require_distinct_active_modifiers(self.modifiers)
        if self.click_count < 1:
            raise ValueError("click_count must be positive")


@dataclass(frozen=True, slots=True)
class DoubleClickOptions:
    """Configuration for a native double click."""

    timeout_ms: int | None = None
    button: MouseButtonLiteral = "left"
    modifiers: tuple[KeyModifier, ...] = ()
    delay_ms: int | None = None
    force: bool = False

    def __post_init__(self) -> None:
        _require_non_negative(timeout_ms=self.timeout_ms, delay_ms=self.delay_ms)
        _require_distinct_active_modifiers(self.modifiers)


@dataclass(frozen=True, slots=True)
class FillOptions:
    """Configuration for replacement input, including an optional clear event."""

    timeout_ms: int | None = None
    clear: bool = False

    def __post_init__(self) -> None:
        _require_non_negative(timeout_ms=self.timeout_ms)


@dataclass(frozen=True, slots=True)
class TypeTextOptions:
    """Configuration for incremental text input."""

    timeout_ms: int | None = None
    delay_ms: int | None = None

    def __post_init__(self) -> None:
        _require_non_negative(timeout_ms=self.timeout_ms, delay_ms=self.delay_ms)


@dataclass(frozen=True, slots=True)
class DragOptions:
    """Element-to-element drag configuration."""

    steps: int = 1
    move_to_center: bool = True
    position_offset: CoordinateType | None = None
    source_offset: CoordinateType | None = None
    target_offset: CoordinateType | None = None

    def __post_init__(self) -> None:
        if self.steps < 1:
            raise ValueError("drag steps must be positive")


def _retain_element(
    element: Element,
    effect: Result[None, Exception],
) -> Result[Element, Exception]:
    if effect.is_error():
        return Error(effect.error)
    return Ok(element)


def _retain_page(
    page: InputPage,
    effect: Result[None, Exception],
) -> Result[InputPage, Exception]:
    if effect.is_error():
        return Error(effect.error)
    return Ok(page)


@result_operation_template
async def Click(
    target: ElementTarget,
    scope: ElementScope,
    *,
    options: ClickOptions | None = None,
) -> Result[Element, Exception]:
    """Click a target and make the acted-on element the next focus."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    configured = options if options is not None else ClickOptions()
    return _retain_element(
        element,
        await element.click(
            timeout_ms=configured.timeout_ms,
            button=configured.button,
            modifiers=configured.modifiers,
            delay_ms=configured.delay_ms,
            click_count=configured.click_count,
            force=configured.force,
        ),
    )


@result_operation_template
async def DoubleClick(
    target: ElementTarget,
    scope: ElementScope,
    *,
    options: DoubleClickOptions | None = None,
) -> Result[Element, Exception]:
    """Double-click a target and make the acted-on element the next focus."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    configured = options if options is not None else DoubleClickOptions()
    return _retain_element(
        element,
        await element.double_click(
            timeout_ms=configured.timeout_ms,
            button=configured.button,
            modifiers=configured.modifiers,
            delay_ms=configured.delay_ms,
            force=configured.force,
        ),
    )


@result_operation_template
async def Fill(
    target: ElementTarget,
    text: str,
    scope: ElementScope,
    *,
    options: FillOptions | None = None,
) -> Result[Element, Exception]:
    """Replace a target's value and make the acted-on element the next focus."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    configured = options if options is not None else FillOptions()
    return _retain_element(
        element,
        await element.fill(
            text,
            timeout_ms=configured.timeout_ms,
            clear=configured.clear,
        ),
    )


@result_operation_template
async def TypeText(
    target: ElementTarget,
    text: str,
    scope: ElementScope,
    *,
    options: TypeTextOptions | None = None,
) -> Result[Element, Exception]:
    """Type into a target and make the acted-on element the next focus."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    configured = options if options is not None else TypeTextOptions()
    return _retain_element(
        element,
        await element.type(
            text,
            timeout_ms=configured.timeout_ms,
            delay_ms=configured.delay_ms,
        ),
    )


@result_operation_template
async def SelectValue(
    target: ElementTarget,
    value: str,
    scope: ElementScope,
) -> Result[Element, Exception]:
    """Select by option value and retain the acted-on element."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    return _retain_element(element, await element.select(value=value))


@result_operation_template
async def SelectText(
    target: ElementTarget,
    text: str,
    scope: ElementScope,
) -> Result[Element, Exception]:
    """Select by visible option text and retain the acted-on element."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    return _retain_element(element, await element.select(text=text))


@result_operation_template
async def ScrollIntoView(
    target: ElementTarget,
    scope: ElementScope,
) -> Result[Element, Exception]:
    """Scroll a target into view and make that element the next focus."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    return _retain_element(element, await element.scroll_into_view())


@result_operation_template
async def MouseMove(
    position: CoordinateType,
    page: InputPage,
    *,
    steps: int = 1,
) -> Result[InputPage, Exception]:
    """Move the pointer to page coordinates and retain page focus."""

    if steps < 1:
        return Error(ValueError("mouse_move steps must be positive"))
    x, y = position
    return _retain_page(
        page,
        await page.mouse_move(x, y, steps=steps),
    )


@result_operation_template
async def MouseMoveTo(
    target: ElementTarget,
    scope: ElementScope,
    *,
    offset: CoordinateType = (0, 0),
    center: bool = True,
    steps: int = 1,
) -> Result[Element, Exception]:
    """Move to an element-relative point and retain that element as focus."""

    if steps < 1:
        return Error(ValueError("mouse_move_to steps must be positive"))
    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok

    moved = await element.move_pointer_to(
        offset=offset,
        center=center,
        steps=steps,
    )
    return _retain_element(element, moved)


@result_operation_template
async def MouseDown(
    page: InputPage,
    *,
    button: MouseButtonLiteral = "left",
) -> Result[InputPage, Exception]:
    """Press a configured mouse button and retain page focus."""

    return _retain_page(page, await page.mouse_down(button=button))


@result_operation_template
async def MouseUp(
    page: InputPage,
    *,
    button: MouseButtonLiteral = "left",
) -> Result[InputPage, Exception]:
    """Release a configured mouse button and retain page focus."""

    return _retain_page(page, await page.mouse_up(button=button))


@result_operation_template
async def KeyPress(
    key: str,
    page: InputPage,
    *,
    delay_ms: int | None = None,
) -> Result[InputPage, Exception]:
    """Press a key and retain page focus."""

    if delay_ms is not None and delay_ms < 0:
        return Error(ValueError("key_press delay_ms must be non-negative"))
    return _retain_page(
        page,
        await page.key_press(key, delay_ms=delay_ms),
    )


@result_operation_template
async def KeyDown(
    key: str,
    page: InputPage,
) -> Result[InputPage, Exception]:
    """Hold a key down and retain page focus."""

    return _retain_page(page, await page.key_down(key))


@result_operation_template
async def KeyUp(
    key: str,
    page: InputPage,
) -> Result[InputPage, Exception]:
    """Release a held key and retain page focus."""

    return _retain_page(page, await page.key_up(key))


@result_operation_template
async def ScrollTo(
    position: CoordinateType,
    page: InputPage,
) -> Result[InputPage, Exception]:
    """Scroll to page coordinates and retain page focus."""

    x, y = position
    return _retain_page(page, await page.scroll(x=x, y=y))


@result_operation_template
async def Drag(
    source: Element,
    target: Element,
    *,
    options: DragOptions | None = None,
) -> Result[Element, Exception]:
    """Drag ``source`` to ``target`` and retain the source as focus.

    Both endpoints must be elements on the same page.
    Bounding-box and pointer errors are returned unchanged.  Coordinates use
    each element's top-left corner unless ``move_to_center`` is enabled; the
    common ``position_offset`` and endpoint-specific offsets are then applied.
    """

    configured = options if options is not None else DragOptions()
    dragged = await source.drag_to(
        target,
        steps=configured.steps,
        move_to_center=configured.move_to_center,
        position_offset=configured.position_offset,
        source_offset=configured.source_offset,
        target_offset=configured.target_offset,
    )
    if dragged.is_error():
        return Error(dragged.error)
    return Ok(source)


__all__ = [
    "ClickOptions",
    "Click",
    "DoubleClickOptions",
    "DoubleClick",
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
]
