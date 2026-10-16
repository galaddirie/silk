"""All-settled teardown contracts for the nominal Playwright driver."""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Browser
from playwright.async_api import BrowserContext as PWBrowserContext
from playwright.async_api import Playwright as PlaywrightAPIType

from silk.browsers.drivers.playwright import _PlaywrightDriver


async def owned_driver(
    *,
    context_failure: BaseException | None = None,
    browser_failure: BaseException | None = None,
    manager_failure: BaseException | None = None,
) -> tuple[_PlaywrightDriver, MagicMock, MagicMock, MagicMock]:
    driver = _PlaywrightDriver()
    browser = MagicMock(spec=Browser)
    context = MagicMock(spec=PWBrowserContext)
    manager = MagicMock(spec=AbstractAsyncContextManager)
    playwright = MagicMock(spec=PlaywrightAPIType)
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock(side_effect=browser_failure)
    context.close = AsyncMock(side_effect=context_failure)
    context.pages = []
    manager.__aexit__ = AsyncMock(side_effect=manager_failure)
    driver._browser = browser
    driver._manager = manager
    driver._playwright = playwright
    context_result = await driver.new_context()
    assert context_result.is_ok()
    return driver, browser, context, manager


@pytest.mark.asyncio
async def test_driver_close_reports_original_context_failure_after_settling_all() -> (
    None
):
    close_error = RuntimeError("context close failed")
    driver, browser, context, manager = await owned_driver(context_failure=close_error)

    outcome = await driver.close()

    assert outcome.is_error()
    assert outcome.error is close_error
    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()
    manager.__aexit__.assert_awaited_once_with(None, None, None)
    assert not driver.has_pending_cleanup
    assert driver._registry.contexts == {}


@pytest.mark.asyncio
async def test_failed_close_retains_retryable_ownership_and_aggregates_exact_causes() -> (
    None
):
    context_error = RuntimeError("context close failed")
    browser_error = RuntimeError("browser close failed")
    manager_error = RuntimeError("manager close failed")
    driver, browser, context, manager = await owned_driver()
    context.close.side_effect = [context_error, None]
    browser.close.side_effect = [browser_error, None]
    manager.__aexit__.side_effect = [manager_error, None]

    first = await driver.close()

    assert first.is_error()
    assert isinstance(first.error, ExceptionGroup)
    assert first.error.exceptions == (
        context_error,
        browser_error,
        manager_error,
    )
    assert driver.has_pending_cleanup
    assert driver._registry.contexts

    second = await driver.close()

    assert second.is_ok(), second
    assert not driver.has_pending_cleanup
    # The failed context is not double-closed before the browser settles it.
    context.close.assert_awaited_once_with()
    assert browser.close.await_count == 2
    assert manager.__aexit__.await_count == 2


@pytest.mark.asyncio
async def test_driver_close_joins_native_cleanup_after_caller_cancellation() -> None:
    driver, browser, context, manager = await owned_driver()
    close_started = asyncio.Event()
    allow_close = asyncio.Event()

    async def blocking_close() -> None:
        close_started.set()
        await allow_close.wait()

    context.close.side_effect = blocking_close
    close_task = asyncio.create_task(driver.close())
    await close_started.wait()
    close_task.cancel("cancelled while closing")
    await asyncio.sleep(0)
    allow_close.set()

    with pytest.raises(asyncio.CancelledError) as raised:
        await close_task

    assert raised.value.args == ("cancelled while closing",)
    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()
    manager.__aexit__.assert_awaited_once_with(None, None, None)
    assert not driver.has_pending_cleanup


@pytest.mark.asyncio
async def test_concurrent_umbrella_closes_are_serialized_and_idempotent() -> None:
    driver, browser, context, manager = await owned_driver()
    close_started = asyncio.Event()
    allow_close = asyncio.Event()

    async def blocking_close() -> None:
        close_started.set()
        await allow_close.wait()

    context.close.side_effect = blocking_close
    first = asyncio.create_task(driver.close())
    await close_started.wait()
    second = asyncio.create_task(driver.close())
    await asyncio.sleep(0)
    allow_close.set()

    assert (await first).is_ok()
    assert (await second).is_ok()
    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()
    manager.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_new_context_queued_behind_close_observes_closed_browser() -> None:
    driver, _browser, context, _manager = await owned_driver()
    close_started = asyncio.Event()
    allow_close = asyncio.Event()

    async def blocking_close() -> None:
        close_started.set()
        await allow_close.wait()

    context.close.side_effect = blocking_close
    close_task = asyncio.create_task(driver.close())
    await close_started.wait()
    create_task = asyncio.create_task(driver.new_context())
    await asyncio.sleep(0)
    assert not create_task.done()
    allow_close.set()

    assert (await close_task).is_ok()
    created = await create_task
    assert created.is_error()
    assert str(created.error) == "Browser not launched"


@pytest.mark.asyncio
async def test_base_exception_propagates_only_after_other_resources_settle() -> None:
    interruption = KeyboardInterrupt("stop")
    driver, browser, context, manager = await owned_driver(context_failure=interruption)

    with pytest.raises(KeyboardInterrupt) as raised:
        await driver.close()

    assert raised.value is interruption
    context.close.assert_awaited_once_with()
    browser.close.assert_awaited_once_with()
    manager.__aexit__.assert_awaited_once_with(None, None, None)
    assert not driver.has_pending_cleanup
