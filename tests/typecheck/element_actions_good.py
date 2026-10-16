# pyright: strict
"""Strict consumer typing for element operation templates."""

from dataclasses import dataclass
from typing import assert_type

from fp_ops import Operation, Result, _, build, traverse

from silk.actions.elements import (
    Element,
    ElementScope,
    ElementTarget,
    SelectorInput,
    WaitPage,
    WaitSelectorInput,
    ElementExists as element_exists,
    ExtractTable as extract_table,
    GetAttribute as get_attribute,
    GetHtml as get_html,
    GetInnerText as get_inner_text,
    GetText as get_text,
    Query as query,
    QueryAll as query_all,
    RequireAttribute as require_attribute,
    RequireElement as require_element,
    WaitForElement as wait_for_element,
)
from silk.browsers.drivers.playwright import (
    PlaywrightElementHandle,
    PlaywrightPage,
)


@dataclass(frozen=True)
class Book:
    title: str
    price: str


def every_placeholder_position(
    selector: SelectorInput,
    target: ElementTarget,
    scope: ElementScope,
    wait_selector: WaitSelectorInput,
    page: WaitPage,
) -> None:
    assert_type(query(_, scope), Operation[SelectorInput, Element | None])
    assert_type(query(selector, _), Operation[ElementScope, Element | None])
    assert_type(require_element(_, scope), Operation[SelectorInput, Element])
    assert_type(require_element(selector, _), Operation[ElementScope, Element])
    assert_type(query_all(_, scope), Operation[SelectorInput, list[Element]])
    assert_type(query_all(selector, _), Operation[ElementScope, list[Element]])
    assert_type(element_exists(_, scope), Operation[SelectorInput, bool])
    assert_type(element_exists(selector, _), Operation[ElementScope, bool])
    assert_type(
        wait_for_element(_, page),
        Operation[WaitSelectorInput, Element | None],
    )
    assert_type(
        wait_for_element(wait_selector, _),
        Operation[WaitPage, Element | None],
    )

    assert_type(get_text(_, scope), Operation[ElementTarget, str])
    assert_type(get_text(target, _), Operation[ElementScope, str])
    assert_type(get_inner_text(_, scope), Operation[ElementTarget, str])
    assert_type(get_inner_text(target, _), Operation[ElementScope, str])
    assert_type(get_html(_, scope), Operation[ElementTarget, str])
    assert_type(get_html(target, _), Operation[ElementScope, str])
    assert_type(
        get_attribute(_, scope, attribute="href"),
        Operation[ElementTarget, str | None],
    )
    assert_type(
        get_attribute(target, _, attribute="href"),
        Operation[ElementScope, str | None],
    )
    assert_type(
        require_attribute(_, scope, attribute="href"),
        Operation[ElementTarget, str],
    )
    assert_type(
        require_attribute(target, _, attribute="href"),
        Operation[ElementScope, str],
    )
    assert_type(
        extract_table(_, scope),
        Operation[ElementTarget, list[dict[str, str]]],
    )
    assert_type(
        extract_table(target, _),
        Operation[ElementScope, list[dict[str, str]]],
    )


extract_book = build(
    {
        "title": require_attribute("h3 > a", _, attribute="title"),
        "price": get_text("p.price_color", _),
    },
    Book,
)
assert_type(extract_book, Operation[ElementScope, Book])

books = query_all("article.product_pod", _) >> traverse(extract_book)
assert_type(books, Operation[ElementScope, list[Book]])


async def playwright_page_is_a_valid_scope(page: PlaywrightPage) -> None:
    lookup = query(".item", _)
    outcome = await lookup.run(page)
    assert_type(outcome, Result[Element | None, Exception])
    wait_outcome = await wait_for_element(".ready", _).run(page)
    assert_type(wait_outcome, Result[Element | None, Exception])


async def playwright_element_is_a_valid_target_and_scope(
    element: PlaywrightElementHandle,
) -> None:
    text_outcome = await get_inner_text(_, element).run(element)
    assert_type(text_outcome, Result[str, Exception])
    list_outcome = await query_all(".item", _).run(element)
    assert_type(list_outcome, Result[list[Element], Exception])
