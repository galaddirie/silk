# pyright: strict
"""Strict consumer typing for the static-HTML backend."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_type

from fp_ops import Operation, Result, _, build, traverse

from silk.actions.elements import (
    Element,
    ElementScope,
    GetText as get_text,
    GetUrl as get_url,
    QueryAll as query_all,
    RequireAttribute as require_attribute,
    WaitForElement as wait_for_element,
    optional,
)
from silk.browsers.models import ElementHandle, Page
from silk.static import (
    HtmlDocument,
    HtmlSource,
    HttpResponseLike,
    ParseHtml as parse_html,
    SnapshotElement as snapshot_element,
    SnapshotPage as snapshot_page,
    StaticElement,
    StaticPage,
    decode_body,
)


@dataclass(frozen=True)
class Book:
    title: str
    price: str
    url: str
    badge: str | None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """The shape of an HTTP client's response, matched structurally."""

    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


extract_book = build(
    {
        "title": require_attribute("h3 > a", _, attribute="title"),
        "price": get_text("p.price_color", _),
        "url": get_url("h3 > a", _),
        "badge": optional(get_text(".badge", _)),
    },
    Book,
)
assert_type(extract_book, Operation[ElementScope, Book])

assert_type(parse_html(_), Operation[HtmlSource, StaticPage])
assert_type(snapshot_page(_), Operation[Page, StaticPage])
assert_type(snapshot_element(_), Operation[ElementHandle, StaticElement])

books_from_html = (
    parse_html(_) >> query_all("article.product_pod", _) >> traverse(extract_book)
)
assert_type(books_from_html, Operation[HtmlSource, list[Book]])

books_from_live_page = (
    snapshot_page(_) >> query_all("article.product_pod", _) >> traverse(extract_book)
)
assert_type(books_from_live_page, Operation[Page, list[Book]])

books_per_snapshot = query_all("article.product_pod", _) >> traverse(
    snapshot_element(_) >> extract_book
)
assert_type(books_per_snapshot, Operation[ElementScope, list[Book]])


def sources_are_accepted(response: HttpResponse) -> None:
    structural: HttpResponseLike = response
    sources: list[HtmlSource] = [
        "<p>x</p>",
        HtmlDocument("<p>x</p>", url="https://example.com/"),
        structural,
        response,
    ]
    assert_type(sources, list[HtmlSource])
    assert_type(decode_body(response.body, response.headers), str)


async def static_values_are_silk_interfaces(html: str) -> None:
    page = StaticPage.from_html(html, url="https://example.com/", base_url=None)
    assert_type(page, StaticPage)
    scope: Page = page
    found = await query_all(".item", _).run(scope)
    assert_type(found, Result[list[Element], Exception])
    waited = await wait_for_element(".item", _).run(page)
    assert_type(waited, Result[Element | None, Exception])

    root = page.root
    assert_type(root, StaticElement)
    assert_type(root.page, StaticPage)
    handle: ElementHandle = root
    text = await get_text(_, handle).run(".item")
    assert_type(text, Result[str, Exception])

    parsed = await parse_html(_).run(HtmlDocument(html))
    assert_type(parsed, Result[StaticPage, Exception])
    snapshot = await snapshot_element(_).run(root)
    assert_type(snapshot, Result[StaticElement, Exception])
