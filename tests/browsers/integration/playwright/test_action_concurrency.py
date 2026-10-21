"""Live Chromium lifecycle through the session's environment browser."""

from __future__ import annotations

import asyncio

import pytest
from fp_ops import _

from silk.actions.browser import (
    CloseContext as close_context,
    CreateContext as create_context,
    NewPage as new_page,
)
from silk.browsers.models import BROWSER, BrowserContextOptions
from silk.browsers.sessions import BrowserSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_context_creation_uses_one_session_browser() -> None:
    async with BrowserSession() as session:
        browser = session.environment.require(BROWSER)
        options = tuple(BrowserContextOptions() for _index in range(4))

        created = await asyncio.gather(
            *(browser.new_context(option) for option in options)
        )

        assert all(outcome.is_ok() for outcome in created), created
        assert len({outcome.ok.context_id for outcome in created}) == len(options)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_created_context_and_page_close_cleanly() -> None:
    async with BrowserSession() as session:
        created = await create_context(_).run(
            BrowserContextOptions(),
            environment=session.environment,
        )
        assert created.is_ok(), created
        context = created.ok
        page_result = await new_page(_).run(context)
        assert page_result.is_ok(), page_result

        closed = await close_context(_).run(context)
        assert closed.is_ok(), closed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_captured_browser_rejects_use_after_session_close() -> None:
    session = await BrowserSession().start()
    browser = session.environment.require(BROWSER)

    await session.close()
    outcome = await browser.new_context(BrowserContextOptions())

    assert outcome.is_error()
    assert isinstance(outcome.error, RuntimeError)
