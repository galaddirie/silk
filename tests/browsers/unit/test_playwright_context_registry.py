"""Focused context/page lifecycle registry contracts."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import _
from playwright.async_api import Browser
from playwright.async_api import BrowserContext as PWBrowserContext
from playwright.async_api import Page as PWPage

from silk.actions.browser import CloseContext as close_context, ClosePage as close_page
from silk.browsers.drivers.playwright import _PlaywrightDriver
from silk.browsers.models import BrowserContext, Page


async def registered_context(
    *,
    context_close: AsyncMock | None = None,
    page_close: AsyncMock | None = None,
) -> tuple[
    _PlaywrightDriver,
    BrowserContext,
    Page,
    MagicMock,
    MagicMock,
]:
    driver = _PlaywrightDriver()
    browser = MagicMock(spec=Browser)
    native_context = MagicMock(spec=PWBrowserContext)
    native_page = MagicMock(spec=PWPage)
    browser.new_context = AsyncMock(return_value=native_context)
    native_context.new_page = AsyncMock(return_value=native_page)
    native_context.close = context_close or AsyncMock(return_value=None)
    native_context.pages = [native_page]
    native_page.close = page_close or AsyncMock(return_value=None)
    driver._browser = browser

    context_result = await driver.new_context()
    assert context_result.is_ok()
    context = context_result.ok
    page_result = await context.new_page()
    assert page_result.is_ok()
    return driver, context, page_result.ok, native_context, native_page


@pytest.mark.asyncio
async def test_failed_context_close_keeps_registry_and_original_error_retryable() -> (
    None
):
    native_error = RuntimeError("native context close failed")
    close = AsyncMock(side_effect=[native_error, None])
    driver, context, _page, native_context, _native_page = await registered_context(
        context_close=close
    )

    failed = await close_context(_).run(context)

    assert failed.is_error()
    assert failed.error is native_error
    assert context.context_id in driver._registry.contexts
    assert context.context_id in driver._registry.close_attempts
    assert driver._registry.contexts[context.context_id] is context

    retried = await close_context(_).run(context)
    assert retried.is_ok(), retried
    assert context.context_id not in driver._registry.contexts
    assert context.context_id not in driver._registry.close_attempts
    assert native_context.close.await_count == 2


@pytest.mark.asyncio
async def test_failed_page_close_preserves_focus_and_is_retryable() -> None:
    native_error = RuntimeError("native page close failed")
    close = AsyncMock(side_effect=[native_error, None])
    _driver, context, page, _native_context, native_page = await registered_context(
        page_close=close
    )

    failed = await close_page(_).run(page)
    listed_after_failure = await context.pages()

    assert failed.is_error()
    assert failed.error is native_error
    assert listed_after_failure.is_ok()
    assert listed_after_failure.ok == [page]
    assert listed_after_failure.ok[0] is page

    retried = await close_page(_).run(page)
    native_page.close.assert_awaited()
    assert retried.is_ok(), retried
    assert close.await_count == 2


@pytest.mark.asyncio
async def test_successful_context_close_invalidates_page_creation_and_is_idempotent() -> (
    None
):
    driver, context, page, native_context, _native_page = await registered_context()

    first = await close_context(_).run(context)
    second = await close_context(_).run(context)
    page_creation = await context.new_page()

    assert first.is_ok(), first
    assert second.is_ok(), second
    assert page_creation.is_error()
    assert context.context_id not in driver._registry.contexts
    native_context.close.assert_awaited_once_with()
    assert (await page.close()).is_ok()


@pytest.mark.asyncio
async def test_page_creation_and_context_close_share_one_lifecycle_lock() -> None:
    driver, context, _page, native_context, _native_page = await registered_context()
    create_started = asyncio.Event()
    allow_create = asyncio.Event()
    created_native_page = MagicMock(spec=PWPage)

    async def blocked_new_page() -> MagicMock:
        create_started.set()
        await allow_create.wait()
        return created_native_page

    native_context.new_page.side_effect = blocked_new_page
    create_task = asyncio.create_task(context.new_page())
    await create_started.wait()
    close_task = asyncio.create_task(context.close())
    await asyncio.sleep(0)
    assert not close_task.done()

    allow_create.set()
    created = await create_task
    closed = await close_task

    assert created.is_ok(), created
    assert closed.is_ok(), closed
    assert context.context_id not in driver._registry.contexts
