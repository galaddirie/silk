"""Browser lifecycle templates with explicit context and page focus.

The driver is stable session capability supplied through the FP-Ops
environment.  Browser contexts and pages are changing pipeline data: creating
or selecting one returns it directly and never updates hidden runner state.
"""

# pyright: strict

from __future__ import annotations

from fp_ops import (
    Error,
    Ok,
    Result,
    environment_result_operation_template,
    result_operation_template,
)

from silk.browsers.capabilities import DRIVER, BrowserDriverCapability
from silk.browsers.models import BrowserContext, BrowserContextOptions, Page
from silk.errors import PageNotFoundError


@environment_result_operation_template(DRIVER)
async def CreateContext(
    options: BrowserContextOptions,
    capability: BrowserDriverCapability,
) -> Result[BrowserContext, Exception]:
    """Create a context from explicit options using the session driver.

    ``options`` is deeply immutable ordinary pipeline data and is safe to
    retain or snapshot without defensive copies.
    """

    return await capability.new_context(options)


@result_operation_template
async def NewPage(
    context: BrowserContext,
) -> Result[Page, Exception]:
    """Create and return a page in ``context``."""

    return await context.new_page()

@result_operation_template
async def Pages(
    context: BrowserContext,
) -> Result[list[Page], Exception]:
    """Return the context's pages in adapter order."""

    return await context.pages()


@result_operation_template
async def PageById(
    page_id: str,
    context: BrowserContext,
) -> Result[Page, Exception]:
    """Select a page by ID, with either operand available as pipeline input.

    Browser failures from listing pages are returned unchanged.  A
    :class:`~silk.errors.PageNotFoundError` is created only after a successful
    listing proves that the requested ID is absent.
    """

    listed = await context.pages()
    if listed.is_error():
        return Error(listed.error)
    for page in listed.ok:
        if page.page_id == page_id:
            return Ok(page)
    return Error(PageNotFoundError(page_id, context_id=context.context_id))


@result_operation_template
async def ClosePage(page: Page) -> Result[None, Exception]:
    """Close a page as a truthful terminal operation."""

    return await page.close()


@result_operation_template
async def CloseContext(
    context: BrowserContext,
) -> Result[None, Exception]:
    """Close a browser context and all of its pages as a terminal operation."""

    return await context.close()


__all__ = [
    "CloseContext",
    "ClosePage",
    "CreateContext",
    "NewPage",
    "PageById",
    "Pages",
]
