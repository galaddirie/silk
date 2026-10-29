"""Browser lifecycle templates with explicit context and page focus.

The :class:`Browser` comes from the FP-Ops environment under ``BROWSER``.
Contexts and pages are ordinary pipeline data: creating or selecting one
returns it directly.
"""

# pyright: strict

from __future__ import annotations

import asyncio

from fp_ops import (
    Error,
    Ok,
    Result,
    environment_result_operation_template,
    result_operation_template,
)

from silk.actions.navigation import NavigateOptions
from silk.browsers.models import (
    BROWSER,
    CONTEXT,
    Browser,
    BrowserContext,
    BrowserContextOptions,
    Page,
)
from silk.errors import PageNotFoundError


@environment_result_operation_template(BROWSER)
async def CreateContext(
    options: BrowserContextOptions | None,
    browser: Browser,
) -> Result[BrowserContext, Exception]:
    """Create a context in the environment's browser.

    ``None`` uses the session's context options.
    """

    return await browser.new_context(options)


async def _settle(
    task: asyncio.Future[Result[Page, Exception]],
) -> Result[Page, Exception] | None:
    """Wait for ``task`` to finish even while being cancelled; ``None`` if it was."""

    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
    if task.cancelled():
        return None
    return task.result()


async def _close_shielded(page: Page) -> None:
    closing = asyncio.ensure_future(page.close())
    while not closing.done():
        try:
            await asyncio.shield(closing)
        except asyncio.CancelledError:
            continue


@environment_result_operation_template(CONTEXT)
async def OpenPage(
    url: str,
    context: BrowserContext,
    *,
    options: NavigateOptions | None = None,
) -> Result[Page, Exception]:
    """Open a new page in the environment's context and navigate it to ``url``.

    If navigation fails the page is closed before the error is returned, so
    this is a safe ``bracket`` acquire step (see :func:`silk.scraping.in_new_page`).
    """

    # Acquire atomically, also under cancellation: a page created or navigating
    # when the caller is cancelled is closed before the cancellation propagates.
    creating = asyncio.ensure_future(context.new_page())
    try:
        created = await asyncio.shield(creating)
    except asyncio.CancelledError:
        orphan = await _settle(creating)
        if orphan is not None and orphan.is_ok():
            await _close_shielded(orphan.ok)
        raise
    if created.is_error():
        return Error(created.error)
    page = created.ok
    configured = options if options is not None else NavigateOptions()
    try:
        navigated = await page.navigate(
            url,
            timeout_ms=configured.timeout,
            wait_until=configured.wait_until,
            referer=configured.referer,
        )
    except BaseException:
        await _close_shielded(page)
        raise
    if navigated.is_error():
        await page.close()
        return Error(navigated.error)
    return Ok(page)


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
    "OpenPage",
    "PageById",
    "Pages",
]
