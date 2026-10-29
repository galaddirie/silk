"""Typed construction-time templates for element lookup and extraction."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urljoin

from fp_ops import (
    Error,
    Ok,
    Operation,
    Result,
    default_on_error,
    result_operation_template,
)

from silk.actions._scope import (
    Element,
    ElementScope,
    ElementTarget,
    SelectorInput,
    SelectorPlan,
    WaitPage,
    WaitSelectorInput,
    query_many,
    query_one,
    require_one,
    require_target,
    snapshot_selector,
    target_reference,
)
from silk.browsers.models import Frame, Page, WaitStateLiteral
from silk.errors import AttributeNotFoundError, ElementNotFoundError, NotFoundError
from silk.selectors.selector import SelectorType

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, slots=True)
class WaitOptions:
    """Selector wait configuration."""

    timeout: int | None = None
    state: WaitStateLiteral = "visible"

    def __post_init__(self) -> None:
        if self.timeout is not None and self.timeout < 0:
            raise ValueError("timeout must be non-negative")


@result_operation_template
async def Query(
    selector: SelectorInput,
    scope: ElementScope,
) -> Result[Element | None, Exception]:
    """Find an element, returning ``None`` only when no selector matches."""

    return await query_one(scope, snapshot_selector(selector))


@result_operation_template
async def RequireElement(
    selector: SelectorInput,
    scope: ElementScope,
) -> Result[Element, Exception]:
    """Find an element or fail with ``ElementNotFoundError``."""

    return await require_one(scope, snapshot_selector(selector))


@result_operation_template
async def QueryAll(
    selector: SelectorInput,
    scope: ElementScope,
) -> Result[list[Element], Exception]:
    """Return the first non-empty fallback as an ordered focus list."""

    return await query_many(scope, snapshot_selector(selector))


@result_operation_template
async def GetText(
    target: ElementTarget,
    scope: ElementScope,
) -> Result[str, Exception]:
    """Read text from a required selector or direct element target."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    return await element_result.ok.text()


@result_operation_template
async def GetAttribute(
    target: ElementTarget,
    scope: ElementScope,
    *,
    attribute: str,
) -> Result[str | None, Exception]:
    """Read an attribute; an absent attribute is a successful ``None``."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    return await element_result.ok.attribute(attribute)


@result_operation_template
async def RequireAttribute(
    target: ElementTarget,
    scope: ElementScope,
    *,
    attribute: str,
) -> Result[str, Exception]:
    """Read an attribute or fail when the target element lacks it."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)

    attribute_result = await element_result.ok.attribute(attribute)
    if attribute_result.is_error():
        return Error(attribute_result.error)
    value = attribute_result.ok
    if value is None:
        return Error(AttributeNotFoundError(target_reference(target), attribute))
    return Ok(value)


@result_operation_template
async def GetHtml(
    target: ElementTarget,
    scope: ElementScope,
    *,
    outer: bool = True,
) -> Result[str, Exception]:
    """Read HTML from a required selector or direct element target."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    return await element_result.ok.html(outer=outer)


@result_operation_template
async def GetInnerText(
    target: ElementTarget,
    scope: ElementScope,
) -> Result[str, Exception]:
    """Read visible text from a required selector or direct element target."""

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    return await element_result.ok.inner_text()


@result_operation_template
async def ElementExists(
    selector: SelectorInput,
    scope: ElementScope,
) -> Result[bool, Exception]:
    """Check selector presence while preserving browser failures."""

    element_result = await query_one(scope, snapshot_selector(selector))
    if element_result.is_error():
        return Error(element_result.error)
    return Ok(element_result.ok is not None)


async def _wait_any(
    page: WaitPage,
    plan: SelectorPlan,
    *,
    timeout_ms: int | None,
    state: WaitStateLiteral,
) -> Result[Element | None, Exception]:
    """Resolve when the first selector reaches ``state``; cancel the others."""

    if all(step.type is SelectorType.CSS for step in plan.selectors):
        # One native wait over a CSS selector list.
        query = ", ".join(step.query for step in plan.selectors)
        return await page.wait_for_selector(query, timeout_ms=timeout_ms, state=state)

    tasks = [
        asyncio.ensure_future(
            page.wait_for_selector(step.query, timeout_ms=timeout_ms, state=state)
        )
        for step in plan.selectors
    ]
    first_error: Exception | None = None
    pending: set[asyncio.Future[Result[Element | None, Exception]]] = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in tasks:
                if task not in done:
                    continue
                outcome = task.result()
                if outcome.is_ok():
                    return outcome
                first_error = first_error or outcome.error
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    assert first_error is not None
    return Error(first_error)


async def _wait_all(
    page: WaitPage,
    plan: SelectorPlan,
    *,
    timeout_ms: int | None,
    state: WaitStateLiteral,
) -> Result[Element | None, Exception]:
    """Resolve once every selector reaches a hidden or detached ``state``."""

    loop = asyncio.get_running_loop()
    deadline = None if timeout_ms is None else loop.time() + timeout_ms / 1000
    for step in plan.selectors:
        remaining = (
            None if deadline is None else max(0, int((deadline - loop.time()) * 1000))
        )
        waited = await page.wait_for_selector(
            step.query, timeout_ms=remaining, state=state
        )
        if waited.is_error():
            return waited
    return Ok(None)


@result_operation_template
async def WaitForElement(
    selector: WaitSelectorInput,
    page: WaitPage,
    *,
    options: WaitOptions | None = None,
) -> Result[Element | None, Exception]:
    """Wait for a selector to reach a state, on a page or a frame.

    With a :class:`SelectorGroup`, ``visible``/``attached`` resolve when *any*
    selector does (returning that element); ``hidden``/``detached`` resolve when
    *all* of them do.
    """

    configured = options if options is not None else WaitOptions()
    plan = snapshot_selector(selector)
    if any(step.type is SelectorType.SELF for step in plan.selectors):
        return Error(TypeError("WaitForElement cannot wait for SELF"))
    if len(plan.selectors) == 1:
        return await page.wait_for_selector(
            plan.selectors[0].query,
            timeout_ms=configured.timeout,
            state=configured.state,
        )
    if configured.state in ("visible", "attached"):
        return await _wait_any(
            page, plan, timeout_ms=configured.timeout, state=configured.state
        )
    return await _wait_all(
        page, plan, timeout_ms=configured.timeout, state=configured.state
    )


@result_operation_template
async def GetUrl(
    target: ElementTarget,
    scope: ElementScope,
    *,
    attribute: str = "href",
) -> Result[str, Exception]:
    """Read a URL attribute resolved against the document's base URL.

    A missing element or attribute is a ``NotFoundError``; relative links,
    ``<base href>`` and protocol-relative URLs resolve like the browser does.
    """

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    element = element_result.ok
    value = await element.attribute(attribute)
    if value.is_error():
        return Error(value.error)
    if value.ok is None:
        return Error(AttributeNotFoundError(target_reference(target), attribute))
    base = await element.page.base_url()
    if base.is_error():
        return Error(base.error)
    return Ok(urljoin(base.ok, value.ok.strip()))


@result_operation_template
async def OwnerPage(element: Element) -> Result[Page, Exception]:
    """The page an element belongs to: ``Click(NEXT, _) >> OwnerPage(_)``."""

    return Ok(element.page)


@result_operation_template
async def ContentFrame(
    target: ElementTarget,
    scope: ElementScope,
) -> Result[Frame, Exception]:
    """The frame hosted by an ``<iframe>`` target; a scope for further lookups.

    Fails with ``ElementNotFoundError`` when the target hosts no frame.
    """

    element_result = await require_target(target, scope)
    if element_result.is_error():
        return Error(element_result.error)
    frame = await element_result.ok.content_frame()
    if frame.is_error():
        return Error(frame.error)
    if frame.ok is None:
        return Error(ElementNotFoundError(target_reference(target)))
    return Ok(frame.ok)


def optional(op: Operation[A, B]) -> Operation[A, B | None]:
    """``None`` when ``op`` finds nothing (``NotFoundError``); other errors stay errors.

    ``optional(GetText(".location", _))`` reads an optional field without hiding
    a browser failure.
    """

    return default_on_error(op, None, on=NotFoundError)


async def _read_table_text(element: Element) -> Result[str, Exception]:
    result = await element.text()
    if result.is_error():
        return Error(result.error)
    return Ok(result.ok.strip())


async def _extract_table(
    target: ElementTarget,
    scope: ElementScope,
    *,
    include_headers: bool,
    header_selector: SelectorInput,
    row_selector: SelectorInput,
    cell_selector: SelectorInput,
) -> Result[list[dict[str, str]], Exception]:
    table_result = await require_target(target, scope)
    if table_result.is_error():
        return Error(table_result.error)
    table = table_result.ok

    headers: list[str] = []
    if include_headers:
        header_result = await query_many(
            table,
            snapshot_selector(header_selector),
        )
        if header_result.is_error():
            return Error(header_result.error)
        for header in header_result.ok:
            text_result = await _read_table_text(header)
            if text_result.is_error():
                return Error(text_result.error)
            headers.append(text_result.ok)

    rows_result = await query_many(table, snapshot_selector(row_selector))
    if rows_result.is_error():
        return Error(rows_result.error)

    output: list[dict[str, str]] = []
    for row in rows_result.ok:
        cells_result = await query_many(row, snapshot_selector(cell_selector))
        if cells_result.is_error():
            return Error(cells_result.error)

        row_data: dict[str, str] = {}
        for index, cell in enumerate(cells_result.ok):
            if headers and index >= len(headers):
                break
            text_result = await _read_table_text(cell)
            if text_result.is_error():
                return Error(text_result.error)
            key = headers[index] if headers else f"column_{index}"
            row_data[key] = text_result.ok
        if row_data:
            output.append(row_data)
    return Ok(output)


@result_operation_template
async def ExtractTable(
    target: ElementTarget,
    scope: ElementScope,
    *,
    include_headers: bool = True,
    header_selector: SelectorInput = "thead th, th",
    row_selector: SelectorInput = "tbody tr, tr",
    cell_selector: SelectorInput = "td",
) -> Result[list[dict[str, str]], Exception]:
    """Extract an HTML table relative to a page or element scope."""

    return await _extract_table(
        target,
        scope,
        include_headers=include_headers,
        header_selector=header_selector,
        row_selector=row_selector,
        cell_selector=cell_selector,
    )


__all__ = [
    "ContentFrame",
    "Element",
    "ElementScope",
    "ElementTarget",
    "ElementExists",
    "ExtractTable",
    "GetAttribute",
    "GetHtml",
    "GetInnerText",
    "GetText",
    "GetUrl",
    "OwnerPage",
    "Query",
    "QueryAll",
    "RequireAttribute",
    "RequireElement",
    "SelectorInput",
    "WaitPage",
    "WaitOptions",
    "WaitForElement",
    "WaitSelectorInput",
    "optional",
]
