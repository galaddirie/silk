"""Scrape the public Books to Scrape catalogue through Silk's public API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fp_ops import (
    EnvKey,
    Operation,
    _,
    build,
    continue_if,
    derive,
    environment_operation_template,
    loop,
    passthrough,
    traverse,
)

from silk.actions.elements import (
    ElementExists,
    ElementScope,
    GetText,
    GetUrl,
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


extract_book: Operation[ElementScope, Book] = build(
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText("p.price_color", _),
    },
    Book,
)

books_pipeline: Operation[Page, list[Book]] = (
    Navigate(_, BOOKS_URL)
    >> QueryAll("article.product_pod", _)
    >> traverse(extract_book)
)


NEXT_PAGE = "li.next > a"


class Shelf:
    """Collects books as each page is read (an app would write them to a file)."""

    def __init__(self) -> None:
        self.books: list[Book] = []


SHELF = EnvKey("shelf", Shelf)


@environment_operation_template(SHELF)
def shelve(books: list[Book], shelf: Shelf) -> list[Book]:
    shelf.books.extend(books)
    return books


books_on_page: Operation[Page, list[Book]] = QueryAll(
    "article.product_pod", _
) >> traverse(extract_book)

# Read a page, shelve its books, then follow "next" until there is none:
# the next URL is read from the page being navigated, with ``derive``.
shelve_page: Operation[Page, Page] = passthrough(books_on_page >> shelve(_))
read_and_advance = shelve_page >> continue_if(
    ElementExists(NEXT_PAGE, _),
    Navigate(_, derive(GetUrl(NEXT_PAGE, _))),
)


def catalogue_pipeline(max_pages: int) -> Operation[Page, Page]:
    """Crawl up to ``max_pages`` catalogue pages in constant stack space."""

    return Navigate(_, BOOKS_URL) >> loop(read_and_advance, max_steps=max_pages)


async def scrape_books() -> list[Book]:
    """Run the pipeline on the session page with the session environment."""

    options = BrowserOptions(headless=True)
    async with BrowserSession(options=options) as session:
        result = await books_pipeline.run(
            session.page,
            environment=session.environment,
        )
        if result.is_error():
            raise result.error
        return result.ok


async def scrape_catalogue(max_pages: int = 50) -> list[Book]:
    """Crawl the whole catalogue (1,000 books over 50 pages)."""

    shelf = Shelf()
    async with BrowserSession(options=BrowserOptions(headless=True)) as session:
        environment = session.environment.with_value(SHELF, shelf)
        result = await catalogue_pipeline(max_pages).run(
            session.page, environment=environment
        )
        if result.is_error():
            raise result.error
    return shelf.books


async def main() -> None:
    books = await scrape_books()
    print(f"Found {len(books)} books")
    for book in books:
        print(f"{book.title} — {book.price}")


if __name__ == "__main__":
    asyncio.run(main())
