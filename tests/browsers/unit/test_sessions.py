from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import Error, Ok, operation

from silk.browsers import (
    BROWSER,
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
    BrowserSession,
    Page,
)
from silk.browsers.drivers.playwright import PlaywrightBrowser


@pytest.fixture
def browser_harness(monkeypatch: pytest.MonkeyPatch):
    page = MagicMock(spec=Page)
    context = MagicMock(spec=BrowserContext)
    context.new_page = AsyncMock(return_value=Ok(page))
    browser = MagicMock(spec=PlaywrightBrowser)
    browser.new_context = AsyncMock(return_value=Ok(context))
    browser.close = AsyncMock(return_value=None)
    launch = AsyncMock(return_value=browser)
    monkeypatch.setattr(PlaywrightBrowser, "launch", launch)
    return launch, browser, context, page


@pytest.mark.asyncio
async def test_started_session_exposes_page_context_and_environment(
    browser_harness,
):
    launch, browser, context, page = browser_harness
    options = BrowserOptions(headless=True)
    context_options = BrowserContextOptions(locale="fr-CA")
    session = BrowserSession(options, context_options=context_options)

    assert await session.start() is session

    assert session.is_started
    assert session.page is page
    assert session.context is context
    assert session.browser is browser
    assert session.environment.require(BROWSER) is browser
    launch.assert_awaited_once_with(options)
    browser.new_context.assert_awaited_once_with(context_options)

    @operation
    def same_page(value: Page) -> Page:
        return value

    result = await same_page.run(session.page, environment=session.environment)
    assert result.ok is page


def test_session_values_are_unavailable_before_start() -> None:
    session = BrowserSession()

    assert not session.is_started
    for name in ("page", "context", "browser", "environment"):
        with pytest.raises(RuntimeError, match="not started"):
            getattr(session, name)


@pytest.mark.asyncio
async def test_start_twice_raises(browser_harness):
    session = BrowserSession()
    await session.start()

    with pytest.raises(RuntimeError, match="already started"):
        await session.start()


@pytest.mark.asyncio
async def test_failed_start_closes_the_browser_and_raises_the_cause(
    browser_harness,
):
    _launch, browser, context, _page = browser_harness
    cause = RuntimeError("page failed")
    context.new_page = AsyncMock(return_value=Error(cause))
    session = BrowserSession()

    with pytest.raises(RuntimeError) as raised:
        await session.start()

    assert raised.value is cause
    browser.close.assert_awaited_once_with()
    assert not session.is_started


@pytest.mark.asyncio
async def test_close_is_idempotent_and_session_can_restart(browser_harness):
    launch, browser, _context, _page = browser_harness
    session = BrowserSession()

    await session.start()
    await session.close()
    await session.close()
    assert not session.is_started
    assert browser.close.await_count == 1

    await session.start()
    assert session.is_started
    assert launch.await_count == 2


@pytest.mark.asyncio
async def test_close_failure_propagates_and_releases_ownership(browser_harness):
    _launch, browser, _context, _page = browser_harness
    cause = RuntimeError("close failed")
    browser.close = AsyncMock(side_effect=cause)
    session = BrowserSession()
    await session.start()

    with pytest.raises(RuntimeError) as raised:
        await session.close()

    assert raised.value is cause
    assert not session.is_started


@pytest.mark.asyncio
async def test_context_manager_closes_after_body_failure(browser_harness):
    _launch, browser, _context, _page = browser_harness

    with pytest.raises(ValueError, match="body"):
        async with BrowserSession():
            raise ValueError("body")

    browser.close.assert_awaited_once_with()
