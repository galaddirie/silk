# pyright: strict
"""Positive typing contracts for browser lifecycle operation templates."""

from collections.abc import Mapping
from typing import assert_type

from fp_ops import Environment, Operation, Result, _

from silk.actions.browser import (
    CloseContext as close_context,
    ClosePage as close_page,
    CreateContext as create_context,
    NewPage as new_page,
    PageById as page_by_id,
    Pages as pages,
)
from silk.browsers.models import (
    BROWSER,
    Browser,
    BrowserContext,
    BrowserContextOptions,
    BrowserProxy,
    BrowserViewport,
    Page,
)


def every_supported_placeholder_position(
    context: BrowserContext,
    page: Page,
    page_id: str,
) -> None:
    assert_type(
        create_context(_),
        Operation[BrowserContextOptions, BrowserContext],
    )
    assert_type(
        new_page(_),
        Operation[BrowserContext, Page],
    )
    assert_type(
        pages(_),
        Operation[BrowserContext, list[Page]],
    )
    assert_type(
        page_by_id(_, context),
        Operation[str, Page],
    )
    assert_type(
        page_by_id(page_id, _),
        Operation[BrowserContext, Page],
    )
    assert_type(close_page(_), Operation[Page, None])
    assert_type(
        close_context(_),
        Operation[BrowserContext, None],
    )

    lifecycle = new_page(_).then(close_page(_))
    assert_type(lifecycle, Operation[BrowserContext, None])


def every_context_option_has_a_precise_type() -> None:
    options = BrowserContextOptions(
        viewport=BrowserViewport(width=1280, height=720),
        permissions=("geolocation",),
        user_agent="SilkContext/1.0",
        extra_http_headers={"x-silk": "typed"},
        proxy=BrowserProxy(server="http://proxy.test:8080"),
        locale="fr-CA",
        timezone_id="America/Toronto",
        timeout=500,
    )

    assert_type(options, BrowserContextOptions)
    assert_type(options.viewport, BrowserViewport | None)
    assert_type(options.permissions, tuple[str, ...] | None)
    assert_type(options.extra_http_headers, Mapping[str, str] | None)
    assert_type(options.proxy, BrowserProxy | None)
    assert_type(options.locale, str | None)
    assert_type(options.timezone_id, str | None)
    assert_type(options.timeout, int | None)


async def public_browser_types_are_valid(
    browser: Browser,
    context: BrowserContext,
    page: Page,
) -> None:
    environment = Environment().with_value(BROWSER, browser)
    assert_type(environment, Environment)

    direct_context_outcome = await browser.new_context(BrowserContextOptions())
    context_outcome = await create_context(_).run(
        BrowserContextOptions(),
        environment=environment,
    )
    page_outcome = await new_page(_).run(context)
    pages_outcome = await pages(_).run(context)
    selected_by_id = await page_by_id(_, context).run(page.page_id)
    selected_by_context = await page_by_id(page.page_id, _).run(context)
    page_close_outcome = await close_page(_).run(page)
    context_close_outcome = await close_context(_).run(context)

    assert_type(
        direct_context_outcome,
        Result[BrowserContext, Exception],
    )
    assert_type(
        context_outcome,
        Result[BrowserContext, Exception],
    )
    assert_type(page_outcome, Result[Page, Exception])
    assert_type(pages_outcome, Result[list[Page], Exception])
    assert_type(selected_by_id, Result[Page, Exception])
    assert_type(selected_by_context, Result[Page, Exception])
    assert_type(page_close_outcome, Result[None, Exception])
    assert_type(context_close_outcome, Result[None, Exception])
