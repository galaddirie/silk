"""Scrape the public Books to Scrape catalogue with Silk's pipeline DSL.

a >> b    then:     feed ``a``'s output into ``b``
a & b     fan out:  run both on the same input concurrently -> ``(a, b)``
a | b     or else:  if ``a`` fails, run ``b`` on the original input
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fp_ops import Operation, _, build, constant, operation, traverse

from silk.actions.elements import (
    ElementScope,
    GetText,
    QueryAll,
    RequireAttribute,
)
from silk.actions.navigation import Navigate
from silk.browsers.models import BrowserOptions, Page
from silk.browsers.sessions import BrowserSession

BOOKS_URL = "https://books.toscrape.com/"


@dataclass(frozen=True, slots=True)
class Book:
    """One immutable catalogue record."""

    title: str
    price: str


@dataclass(frozen=True, slots=True)
class Catalogue:
    """The first catalogue page and its summary."""

    total: int
    page: str
    books: list[Book]


extract_book: Operation[ElementScope, Book] = build(
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText("p.price_color", _),
    },
    Book,
)

books_on_page = QueryAll("article.product_pod", _) >> traverse(extract_book)

books_pipeline: Operation[Page, list[Book]] = Navigate(_, BOOKS_URL) >> books_on_page

result_count = GetText("form.form-horizontal strong", _).map(int)

# A single-page catalogue renders no pager.
page_label = GetText("li.current", _).map(str.strip) | constant("Page 1 of 1")


@operation
def to_catalogue(parts: tuple[int, str, list[Book]]) -> Catalogue:
    total, page, books = parts
    return Catalogue(total=total, page=page, books=books)


catalogue_pipeline: Operation[Page, Catalogue] = (
    Navigate(_, BOOKS_URL)
    >> (result_count & page_label & books_on_page)
    >> to_catalogue
)


async def scrape_catalogue() -> Catalogue:
    """Run the pipeline on the session page with the session environment."""

    options = BrowserOptions(headless=True)
    async with BrowserSession(options=options) as session:
        result = await catalogue_pipeline.run(
            session.page,
            environment=session.environment,
        )
        if result.is_error():
            raise result.error
        return result.ok


async def main() -> None:
    catalogue = await scrape_catalogue()
    print(f"{catalogue.total} books — {catalogue.page}")
    for book in catalogue.books:
        print(f"{book.title} — {book.price}")


if __name__ == "__main__":
    asyncio.run(main())
