# pyright: strict
"""Internal selector resolution for page and element scopes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeAlias

from fp_ops import Error, Ok, Result

from silk.browsers.models import ElementHandle, Page
from silk.errors import ElementNotFoundError, SelectorReference
from silk.selectors.selector import Selector, SelectorGroup, SelectorType

Element: TypeAlias = ElementHandle
SelectorInput: TypeAlias = str | Selector | SelectorGroup
WaitSelectorInput: TypeAlias = str | Selector
ElementTarget: TypeAlias = SelectorInput | Element


ElementScope: TypeAlias = Page | Element
WaitPage: TypeAlias = Page


@dataclass(frozen=True, slots=True)
class SelectorStep:
    """One immutable selector with its native query representation."""

    type: SelectorType
    value: str
    query: str


@dataclass(frozen=True, slots=True)
class SelectorPlan:
    """An immutable ordered selector fallback plan."""

    selectors: tuple[SelectorStep, ...]

    @property
    def reference(self) -> SelectorReference:
        values = tuple(selector.value for selector in self.selectors)
        if len(values) == 1:
            return values[0]
        return values


def _quoted_css_value(value: str) -> str:
    return json.dumps(value)


def _compile_selector(selector_type: SelectorType, value: str) -> str:
    if selector_type is SelectorType.CSS:
        return value
    if selector_type is SelectorType.XPATH:
        return f"xpath={value}"
    if selector_type is SelectorType.TEXT:
        return f"text={value}"
    if selector_type is SelectorType.ID:
        return f"[id={_quoted_css_value(value)}]"
    if selector_type is SelectorType.CLASS:
        return f"[class~={_quoted_css_value(value)}]"
    if selector_type is SelectorType.NAME:
        return f"[name={_quoted_css_value(value)}]"
    if selector_type is SelectorType.TAG:
        return value
    if selector_type is SelectorType.LINK_TEXT:
        return f"a:text-is({_quoted_css_value(value)})"
    raise ValueError(f"unsupported selector type: {selector_type!r}")


def _snapshot_step(selector: Selector) -> SelectorStep:
    selector_type = SelectorType(selector.type)
    value = selector.value
    return SelectorStep(
        type=selector_type,
        value=value,
        query=_compile_selector(selector_type, value),
    )


def snapshot_selector(selector: SelectorInput) -> SelectorPlan:
    """Copy mutable selector configuration into an immutable plan."""

    if isinstance(selector, str):
        return SelectorPlan(
            (
                SelectorStep(
                    type=SelectorType.CSS,
                    value=selector,
                    query=selector,
                ),
            )
        )
    if isinstance(selector, Selector):
        return SelectorPlan((_snapshot_step(selector),))
    return SelectorPlan(
        tuple(_snapshot_step(item) for item in selector.selectors),
    )


def snapshot_wait_selector(selector: WaitSelectorInput) -> SelectorStep:
    """Compile one wait selector; selector groups have no coherent wait policy."""

    if isinstance(selector, str):
        return SelectorStep(
            type=SelectorType.CSS,
            value=selector,
            query=selector,
        )
    return _snapshot_step(selector)


async def query_one(
    scope: ElementScope,
    plan: SelectorPlan,
) -> Result[Element | None, Exception]:
    """Resolve the first present selector without treating errors as absence."""

    for selector in plan.selectors:
        result = await scope.query_selector(selector.query)
        if result.is_error():
            return Error(result.error)
        element: Element | None = result.ok
        if element is not None:
            return Ok(element)
    return Ok(None)


async def require_one(
    scope: ElementScope,
    plan: SelectorPlan,
) -> Result[Element, Exception]:
    """Resolve one element or return a domain not-found error."""

    result = await query_one(scope, plan)
    if result.is_error():
        return Error(result.error)
    element = result.ok
    if element is None:
        return Error(ElementNotFoundError(plan.reference))
    return Ok(element)


async def require_target(
    target: ElementTarget,
    scope: ElementScope,
) -> Result[Element, Exception]:
    """Resolve a selector target or retain a direct element target."""

    if isinstance(target, (str, Selector, SelectorGroup)):
        return await require_one(scope, snapshot_selector(target))
    return Ok(target)


def target_reference(target: ElementTarget) -> SelectorReference:
    """Return a stable diagnostic reference for a selector or element target."""

    if isinstance(target, (str, Selector, SelectorGroup)):
        return snapshot_selector(target).reference
    selector = target.selector
    return selector if selector is not None else "<element>"


async def query_many(
    scope: ElementScope,
    plan: SelectorPlan,
) -> Result[list[Element], Exception]:
    """Resolve the first non-empty selector into an explicit focus list."""

    for selector in plan.selectors:
        result = await scope.query_selector_all(selector.query)
        if result.is_error():
            return Error(result.error)
        elements: list[Element] = result.ok
        if elements:
            return Ok(list(elements))
    return Ok([])


__all__ = [
    "Element",
    "ElementScope",
    "ElementTarget",
    "SelectorInput",
    "SelectorPlan",
    "SelectorStep",
    "WaitPage",
    "WaitSelectorInput",
    "query_many",
    "query_one",
    "require_one",
    "require_target",
    "snapshot_selector",
    "snapshot_wait_selector",
    "target_reference",
]
