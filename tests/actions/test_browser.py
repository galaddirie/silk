"""Public-interface contracts for browser lifecycle operation templates."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import Environment, EnvironmentError, Error, Ok, Operation, _

import silk.actions.browser as browser_actions
from silk.actions.browser import (
    CloseContext as close_context,
    ClosePage as close_page,
    CreateContext as create_context,
    NewPage as new_page,
    PageById as page_by_id,
    Pages as pages,
)
from silk.browsers.capabilities import (
    DRIVER,
    BrowserDriverCapability,
    BrowserSessionInfo,
)
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserHttpHeaders,
    BrowserOptions,
    BrowserViewport,
    Page,
)
from silk.browsers.sessions import BrowserSession
from silk.errors import PageNotFoundError


def make_page(page_id: str) -> MagicMock:
    """Return an identity-preserving page double at the public seam."""

    page = MagicMock(spec=Page)
    page.page_id = page_id
    page.close = AsyncMock(return_value=Ok(None))
    page.__copy__.return_value = page
    page.__deepcopy__.return_value = page
    return page


def make_context(
    context_id: str,
    page_values: list[Page] | None = None,
) -> MagicMock:
    """Return an identity-preserving browser-context double."""

    context = MagicMock(spec=BrowserContext)
    context.context_id = context_id
    context.new_page = AsyncMock(return_value=Ok(make_page("new-page")))
    context.pages = AsyncMock(return_value=Ok(page_values or []))
    context.close = AsyncMock(return_value=Ok(None))
    context.__copy__.return_value = context
    context.__deepcopy__.return_value = context
    return context


def make_driver(context: BrowserContext) -> MagicMock:
    """Return a driver double accepted by the typed capability wrapper."""

    driver = MagicMock()
    driver.new_context = AsyncMock(return_value=Ok(context))
    return driver


@pytest.mark.asyncio
async def test_create_context_uses_the_exact_driver_capability() -> None:
    context = make_context("created")
    driver = make_driver(context)
    capability = BrowserDriverCapability(driver.new_context)
    environment = Environment().with_value(DRIVER, capability)
    options = BrowserContextOptions(
        viewport=BrowserViewport(width=1024, height=768),
        permissions=("clipboard-read",),
    )

    outcome = await create_context(_).run(options, environment=environment)

    assert outcome == Ok(context)
    assert outcome.ok is context
    assert environment.require(DRIVER) is capability
    assert not hasattr(capability, "driver")
    driver.new_context.assert_awaited_once_with(options)


@pytest.mark.asyncio
async def test_create_context_hands_the_adapter_the_immutable_options() -> None:
    context = make_context("created")
    driver = make_driver(context)
    received: list[BrowserContextOptions] = []

    async def capture_adapter_options(
        options: BrowserContextOptions | None,
    ) -> object:
        assert options is not None
        received.append(options)
        return Ok(context)

    driver.new_context.side_effect = capture_adapter_options
    original = BrowserContextOptions(
        viewport=BrowserViewport(width=1440, height=900),
        permissions=("geolocation",),
        extra_http_headers=BrowserHttpHeaders({"x-test": "original"}),
    )
    environment = Environment().with_value(
        DRIVER,
        BrowserDriverCapability(driver.new_context),
    )

    outcome = await create_context(_).run(original, environment=environment)

    assert outcome.ok is context
    assert received[0] is original
    assert original.viewport == BrowserViewport(width=1440, height=900)
    assert original.permissions == ("geolocation",)
    assert dict(original.extra_http_headers or {}) == {"x-test": "original"}


@pytest.mark.asyncio
async def test_create_context_requires_the_driver_before_running() -> None:
    options = BrowserContextOptions()

    outcome = await create_context(_).run(options)

    assert outcome.is_error()
    assert isinstance(outcome.error, EnvironmentError)
    assert "browser_driver" in str(outcome.error)


def test_environment_rejects_the_wrong_driver_capability() -> None:
    wrong = BrowserSessionInfo(session_id="not-a-driver")

    with pytest.raises(EnvironmentError, match="BrowserDriverCapability"):
        Environment().with_value(DRIVER, wrong)


@pytest.mark.asyncio
async def test_create_context_preserves_the_browser_error_object() -> None:
    context = make_context("unused")
    driver = make_driver(context)
    browser_error = RuntimeError("browser disconnected")
    driver.new_context.return_value = Error(browser_error)
    environment = Environment().with_value(
        DRIVER,
        BrowserDriverCapability(driver.new_context),
    )

    outcome = await create_context(_).run(
        BrowserContextOptions(),
        environment=environment,
    )

    assert outcome.is_error()
    assert outcome.error is browser_error


@pytest.mark.asyncio
async def test_created_context_flows_directly_into_page_creation() -> None:
    page = make_page("composed-page")
    context = make_context("composed-context")
    context.new_page.return_value = Ok(page)
    driver = make_driver(context)
    environment = Environment().with_value(
        DRIVER,
        BrowserDriverCapability(driver.new_context),
    )
    lifecycle = create_context(_).then(new_page(_))

    outcome = await lifecycle.run(
        BrowserContextOptions(),
        environment=environment,
    )

    assert outcome.ok is page
    context.new_page.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_new_page_and_pages_return_exact_browser_focus_values() -> None:
    first = make_page("first")
    second = make_page("second")
    context = make_context("context", [first, second])
    context.new_page.return_value = Ok(second)

    created = await new_page(_).run(context)
    listed = await pages(_).run(context)

    assert created.ok is second
    assert listed.ok[0] is first
    assert listed.ok[1] is second
    context.new_page.assert_awaited_once_with()
    context.pages.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_page_by_id_supports_both_pipeline_operand_positions() -> None:
    first = make_page("first")
    second = make_page("second")
    context = make_context("context", [first, second])

    dynamic_id = await page_by_id(_, context).run("second")
    dynamic_context = await page_by_id("first", _).run(context)

    assert dynamic_id.ok is second
    assert dynamic_context.ok is first
    assert context.pages.await_count == 2


@pytest.mark.asyncio
async def test_page_by_id_reports_only_proven_absence() -> None:
    context = make_context("context-7", [make_page("present")])

    outcome = await page_by_id("missing", _).run(context)

    assert outcome.is_error()
    assert isinstance(outcome.error, PageNotFoundError)
    assert outcome.error.page_id == "missing"
    assert outcome.error.context_id == "context-7"
    assert outcome.error.__cause__ is None


@pytest.mark.asyncio
async def test_page_by_id_does_not_translate_a_listing_failure() -> None:
    context = make_context("context")
    browser_error = RuntimeError("target closed")
    context.pages.return_value = Error(browser_error)

    outcome = await page_by_id("anything", _).run(context)

    assert outcome.is_error()
    assert outcome.error is browser_error


@pytest.mark.asyncio
async def test_close_actions_are_terminal_and_preserve_failures() -> None:
    page = make_page("page")
    context = make_context("context")

    page_outcome = await close_page(_).run(page)
    context_outcome = await close_context(_).run(context)

    assert page_outcome == Ok(None)
    assert context_outcome == Ok(None)
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()

    page_error = RuntimeError("page close failed")
    context_error = RuntimeError("context close failed")
    page.close.return_value = Error(page_error)
    context.close.return_value = Error(context_error)

    failed_page = await close_page(_).run(page)
    failed_context = await close_context(_).run(context)

    assert failed_page.error is page_error
    assert failed_context.error is context_error


@pytest.mark.asyncio
async def test_new_page_and_pages_preserve_browser_failures() -> None:
    context = make_context("context")
    new_page_error = RuntimeError("new page failed")
    pages_error = RuntimeError("list pages failed")
    context.new_page.return_value = Error(new_page_error)

    created = await new_page(_).run(context)
    context.pages.return_value = Error(pages_error)
    listed = await pages(_).run(context)

    assert created.error is new_page_error
    assert listed.error is pages_error


def test_templates_require_exactly_one_direct_placeholder() -> None:
    context = make_context("context")
    page = make_page("page")

    zero_hole_calls = (
        lambda: create_context(BrowserContextOptions()),
        lambda: new_page(context),
        lambda: pages(context),
        lambda: page_by_id("page", context),
        lambda: close_page(page),
        lambda: close_context(context),
    )
    for call in zero_hole_calls:
        with pytest.raises(TypeError, match="exactly one direct placeholder"):
            call()

    with pytest.raises(TypeError, match="exactly one direct placeholder"):
        page_by_id(_, _)
    with pytest.raises(TypeError):
        new_page(_, _)


def test_public_surface_contains_pascal_case_lifecycle_templates() -> None:
    expected = {
        "CloseContext",
        "ClosePage",
        "CreateContext",
        "NewPage",
        "PageById",
        "Pages",
    }

    assert set(browser_actions.__all__) == expected
    assert inspect.signature(create_context).parameters.keys() == {"options"}
    assert inspect.signature(page_by_id).parameters.keys() == {
        "page_id",
        "context",
    }
    assert all(name[0].isupper() for name in browser_actions.__all__)
    assert not hasattr(browser_actions, "create_context")
    assert create_context.__name__ == "CreateContext"

    operations = (
        create_context(_),
        new_page(_),
        pages(_),
        page_by_id("page", _),
        close_page(_),
        close_context(_),
    )
    assert all(isinstance(operation, Operation) for operation in operations)
    assert all(not callable(operation) for operation in operations)
    assert all(not hasattr(operation, "execute") for operation in operations)
    assert create_context(_).required_environment == (DRIVER,)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_chromium_context_and_page_lifecycle() -> None:
    """Exercise the public lifecycle interface against a real browser."""

    async with BrowserSession(
        options=BrowserOptions(headless=True, timeout=10_000),
    ) as session:
        created = await create_context(_).run(
            BrowserContextOptions(
                viewport=BrowserViewport(width=800, height=600),
            ),
            environment=session.environment,
        )
        assert created.is_ok(), created
        second_context = created.ok

        first_page_outcome = await new_page(_).run(second_context)
        second_page_outcome = await new_page(_).run(second_context)
        assert first_page_outcome.is_ok(), first_page_outcome
        assert second_page_outcome.is_ok(), second_page_outcome
        first_page = first_page_outcome.ok
        second_page = second_page_outcome.ok

        listed = await pages(_).run(second_context)
        assert listed.is_ok(), listed
        assert [page.page_id for page in listed.ok] == [
            first_page.page_id,
            second_page.page_id,
        ]

        selected_by_id = await page_by_id(_, second_context).run(second_page.page_id)
        selected_by_context = await page_by_id(first_page.page_id, _).run(
            second_context
        )
        assert selected_by_id.ok.page_id == second_page.page_id
        assert selected_by_context.ok.page_id == first_page.page_id

        closed_page = await close_page(_).run(first_page)
        assert closed_page == Ok(None)
        remaining = await pages(_).run(second_context)
        assert remaining.is_ok(), remaining
        assert [page.page_id for page in remaining.ok] == [second_page.page_id]

        closed_context = await close_context(_).run(second_context)
        assert closed_context == Ok(None)
