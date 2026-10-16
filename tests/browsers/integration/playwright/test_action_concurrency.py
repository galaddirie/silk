"""Live Chromium lifecycle serialization through session capabilities."""

from __future__ import annotations

import asyncio

import pytest
from fp_ops import _

from silk.actions.browser import (
    CloseContext as close_context,
    CreateContext as create_context,
    NewPage as new_page,
)
from silk.browsers.capabilities import DRIVER, BrowserSessionNotStartedError
from silk.browsers.models import BrowserContextOptions
from silk.browsers.sessions import BrowserSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_capability_creation_uses_one_public_session() -> None:
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)
    options = tuple(BrowserContextOptions() for _index in range(4))

    created = await asyncio.gather(
        *(capability.new_context(option) for option in options)
    )

    assert all(outcome.is_ok() for outcome in created), created
    assert len({outcome.ok.context_id for outcome in created}) == len(options)
    assert await session.close_all_settled() == ()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_cleanup_callers_settle_one_public_owner() -> None:
    session = await BrowserSession().start()

    reports = await asyncio.gather(
        session.close_all_settled(),
        session.close_all_settled(),
        session.close_all_settled(),
    )

    assert len(reports) == 3
    assert all(report == () for report in reports)
    assert session.is_started is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_capability_focus_has_no_umbrella_or_native_escape() -> None:
    async with BrowserSession() as session:
        capability = session.environment.require(DRIVER)
        created = await create_context(_).run(
            BrowserContextOptions(),
            environment=session.environment,
        )
        assert created.is_ok(), created
        context = created.ok
        page_result = await new_page(_).run(context)
        assert page_result.is_ok(), page_result
        page = page_result.ok
        element_result = await page.query_selector("body")
        assert element_result.is_ok() and element_result.ok is not None
        element = element_result.ok

        assert not hasattr(capability, "driver")
        for focus in (context, page, element):
            assert not hasattr(focus, "driver")
            assert not hasattr(focus, "driver_ref")
            assert not hasattr(focus, "context_ref")
            assert not hasattr(focus, "page_ref")
            assert not hasattr(focus, "element_ref")
            assert not hasattr(focus, "as_native")

        closed = await close_context(_).run(context)
        assert closed.is_ok(), closed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_captured_capability_rejects_use_after_cleanup() -> None:
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)

    assert await session.close_all_settled() == ()
    outcome = await capability.new_context(BrowserContextOptions())

    assert outcome.is_error()
    assert isinstance(outcome.error, BrowserSessionNotStartedError)
