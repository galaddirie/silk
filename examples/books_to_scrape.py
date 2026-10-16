"""Scrape the public Books to Scrape catalogue through Silk's public API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fp_ops import Operation, _, build, traverse

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


extract_book = build(
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText("p.price_color", _),
    },
    Book,
)

books_pipeline = (
    Navigate(_, BOOKS_URL)
    .then(QueryAll("article.product_pod", _))
    .then(traverse(extract_book))
)


async def scrape_books() -> list[Book]:
    """Run the pipeline with explicit page focus and session capabilities."""

    options = BrowserOptions(headless=True)
    async with BrowserSession(options=options) as session:
        result = await books_pipeline.run(
            session.page,
            environment=session.environment,
        )
        if result.is_error():
            raise result.error
        return result.ok


async def main() -> None:
    books = await scrape_books()
    print(f"Found {len(books)} books")
    for book in books:
        print(f"{book.title} — {book.price}")


if __name__ == "__main__":
    asyncio.run(main())
