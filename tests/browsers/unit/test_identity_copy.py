"""Nominal focus identity and concrete Playwright escape contracts."""

from __future__ import annotations

from copy import copy, deepcopy
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import Ok, Result, _, result_operation_template
from playwright.async_api import Browser
from playwright.async_api import BrowserContext as PWBrowserContext
from playwright.async_api import ElementHandle as PWElementHandle
from playwright.async_api import Page as PWPage

from silk.browsers.drivers.playwright import _PlaywrightDriver
from silk.browsers.models import BrowserContext, ElementHandle, Page


class _EmptyPage(Page):
    pass


class _EmptyBrowserContext(BrowserContext):
    pass


class _EmptyElementHandle(ElementHandle):
    pass


async def adapter_values() -> tuple[Page, BrowserContext, ElementHandle]:
    driver = _PlaywrightDriver()
    browser = MagicMock(spec=Browser)
    native_context = MagicMock(spec=PWBrowserContext)
    native_page = MagicMock(spec=PWPage)
    native_element = MagicMock(spec=PWElementHandle)
    browser.new_context = AsyncMock(return_value=native_context)
    native_context.new_page = AsyncMock(return_value=native_page)
    native_context.pages = [native_page]
    native_page.query_selector = AsyncMock(return_value=native_element)
    driver._browser = browser

    context_result = await driver.new_context()
    assert context_result.is_ok()
    context = context_result.ok
    page_result = await context.new_page()
    assert page_result.is_ok()
    page = page_result.ok
    element_result = await page.query_selector(".item")
    assert element_result.is_ok() and element_result.ok is not None
    return page, context, element_result.ok


@pytest.mark.asyncio
async def test_playwright_browser_handles_preserve_identity_when_copied() -> None:
    page, context, element = await adapter_values()

    for focus in (page, context, element):
        assert copy(focus) is focus
        assert deepcopy(focus) is focus
        assert not hasattr(focus, "driver")
        assert not hasattr(focus, "driver_ref")
        assert not hasattr(focus, "page_ref")
        assert not hasattr(focus, "context_ref")
        assert not hasattr(focus, "element_ref")
        assert not hasattr(focus, "as_native")
    for obsolete_element_member in (
        "element_id",
        "_pointer_owner_identity",
        "_bounding_box",
        "_move_pointer",
        "_drag_pointer",
    ):
        assert not hasattr(element, obsolete_element_member)


@pytest.mark.parametrize(
    "focus_type",
    (
        Page,
        BrowserContext,
        ElementHandle,
        _EmptyPage,
        _EmptyBrowserContext,
        _EmptyElementHandle,
    ),
)
def test_incomplete_browser_focus_contracts_cannot_be_instantiated(
    focus_type: type[object],
) -> None:
    with pytest.raises(TypeError, match="abstract"):
        focus_type()


@pytest.mark.asyncio
async def test_playwright_focus_adapters_are_nominal_and_concrete() -> None:
    page, context, element = await adapter_values()

    assert isinstance(page, Page)
    assert isinstance(context, BrowserContext)
    assert isinstance(element, ElementHandle)
    assert type(page).__abstractmethods__ == frozenset()
    assert type(context).__abstractmethods__ == frozenset()
    assert type(element).__abstractmethods__ == frozenset()


@pytest.mark.asyncio
async def test_templates_preserve_exact_focus_identity() -> None:
    page, context, element = await adapter_values()

    @result_operation_template
    def retain_page(left: Page, right: Page) -> Result[Page, Exception]:
        assert left is page
        return Ok(right)

    @result_operation_template
    def retain_context(
        left: BrowserContext,
        right: BrowserContext,
    ) -> Result[BrowserContext, Exception]:
        assert left is context
        return Ok(right)

    @result_operation_template
    def retain_element(
        left: ElementHandle,
        right: ElementHandle,
    ) -> Result[ElementHandle, Exception]:
        assert left is element
        return Ok(right)

    assert (await retain_page(page, _).run(page)).ok is page
    assert (await retain_context(context, _).run(context)).ok is context
    assert (await retain_element(element, _).run(element)).ok is element
