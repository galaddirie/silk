# pyright: strict
"""Strict consumer typing for identity-preserving Playwright handles."""

from __future__ import annotations

from copy import copy, deepcopy
from typing import assert_type

from fp_ops import Ok, Operation, Result, _, result_operation_template

from silk.browsers.drivers.playwright import (
    PlaywrightBrowserContext,
    PlaywrightElementHandle,
    PlaywrightPage,
)
from silk.browsers.models import BrowserContext, ElementHandle, Page


@result_operation_template
def choose_page(
    left: Page,
    right: Page,
) -> Result[Page, Exception]:
    return Ok(left)


@result_operation_template
def choose_context(
    left: BrowserContext,
    right: BrowserContext,
) -> Result[BrowserContext, Exception]:
    return Ok(left)


@result_operation_template
def choose_element(
    left: ElementHandle,
    right: ElementHandle,
) -> Result[ElementHandle, Exception]:
    return Ok(left)


def concrete_adapters_preserve_copy_types(
    page: PlaywrightPage,
    context: PlaywrightBrowserContext,
    element: PlaywrightElementHandle,
) -> None:
    page_protocol: Page = page
    context_protocol: BrowserContext = context
    element_protocol: ElementHandle = element

    assert_type(copy(page), PlaywrightPage)
    assert_type(deepcopy(page), PlaywrightPage)
    assert_type(page.__copy__(), PlaywrightPage)
    assert_type(page.__deepcopy__({}), PlaywrightPage)

    assert_type(copy(context), PlaywrightBrowserContext)
    assert_type(deepcopy(context), PlaywrightBrowserContext)
    assert_type(context.__copy__(), PlaywrightBrowserContext)
    assert_type(context.__deepcopy__({}), PlaywrightBrowserContext)

    assert_type(copy(element), PlaywrightElementHandle)
    assert_type(deepcopy(element), PlaywrightElementHandle)
    assert_type(element.__copy__(), PlaywrightElementHandle)
    assert_type(element.__deepcopy__({}), PlaywrightElementHandle)

    _ = page_protocol, context_protocol, element_protocol


def concrete_adapters_configure_either_template_position(
    page: PlaywrightPage,
    context: PlaywrightBrowserContext,
    element: PlaywrightElementHandle,
) -> None:
    assert_type(
        choose_page(page, _),
        Operation[Page, Page],
    )
    assert_type(
        choose_page(_, page),
        Operation[Page, Page],
    )
    assert_type(
        choose_context(context, _),
        Operation[BrowserContext, BrowserContext],
    )
    assert_type(
        choose_context(_, context),
        Operation[BrowserContext, BrowserContext],
    )
    assert_type(
        choose_element(element, _),
        Operation[ElementHandle, ElementHandle],
    )
    assert_type(
        choose_element(_, element),
        Operation[ElementHandle, ElementHandle],
    )
