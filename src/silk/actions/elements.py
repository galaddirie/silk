"""Typed construction-time templates for element lookup and extraction."""

from __future__ import annotations

from dataclasses import dataclass

from fp_ops import Error, Ok, Result, result_operation_template

from silk.actions._scope import (
    Element,
    ElementScope,
    ElementTarget,
    SelectorInput,
    WaitPage,
    WaitSelectorInput,
    query_many,
    query_one,
    require_one,
    require_target,
    snapshot_selector,
    snapshot_wait_selector,
    target_reference,
)
from silk.browsers.models import WaitStateLiteral
from silk.errors import AttributeNotFoundError


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


@result_operation_template
async def WaitForElement(
    selector: WaitSelectorInput,
    page: WaitPage,
    *,
    options: WaitOptions | None = None,
) -> Result[Element | None, Exception]:
    """Wait for one selector using the page's explicit wait-state policy."""

    compiled = snapshot_wait_selector(selector)
    configured = options if options is not None else WaitOptions()
    return await page.wait_for_selector(
        compiled.query,
        timeout_ms=configured.timeout,
        state=configured.state,
    )


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
    "Element",
    "ElementScope",
    "ElementTarget",
    "ElementExists",
    "ExtractTable",
    "GetAttribute",
    "GetHtml",
    "GetInnerText",
    "GetText",
    "Query",
    "QueryAll",
    "RequireAttribute",
    "RequireElement",
    "SelectorInput",
    "WaitPage",
    "WaitOptions",
    "WaitForElement",
    "WaitSelectorInput",
]
