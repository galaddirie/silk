"""Runtime contracts for the public Books to Scrape pipeline."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from importlib import util
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import BuildFieldError, Error, Ok, TraversalItemError

from silk.browsers.models import BrowserOptions, ElementHandle, Page
from silk.browsers.sessions import BrowserSession


def load_books_example() -> ModuleType:
    """Load the checked example by path under every supported pytest launcher."""

    path = Path(__file__).parents[2] / "examples" / "books_to_scrape.py"
    spec = util.spec_from_file_location("silk_books_to_scrape_example", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load books example from {path}")
    module = util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


books_example = load_books_example()
Book = books_example.Book
books_pipeline = books_example.books_pipeline


@pytest.mark.asyncio
async def test_real_books_pipeline_runs_end_to_end_in_chromium() -> None:
    async with BrowserSession(
        options=BrowserOptions(headless=True),
    ) as session:
        result = await books_pipeline.run(
            session.page,
            environment=session.environment,
        )

    assert result.is_ok()
    assert len(result.ok) == 20
    assert result.ok[0] == Book(
        title="A Light in the Attic",
        price="£51.77",
    )
    assert result.ok[-1] == Book(
        title="It's Only the Himalayas",
        price="£45.17",
    )
    assert all(book.title and book.price.startswith("£") for book in result.ok)

    with pytest.raises(FrozenInstanceError):
        result.ok[0].title = "mutated"


@pytest.mark.asyncio
async def test_browser_error_survives_traversal_and_book_construction() -> None:
    browser_error = RuntimeError("browser target closed")
    anchor = MagicMock(spec=ElementHandle)
    anchor.attribute = AsyncMock(return_value=Error(browser_error))

    element = MagicMock(spec=ElementHandle)
    element.query_selector = AsyncMock(return_value=Ok(anchor))
    element.text = AsyncMock(return_value=Ok("£0.00"))

    page = MagicMock(spec=Page)
    page.navigate = AsyncMock(return_value=Ok(None))
    page.query_selector_all = AsyncMock(return_value=Ok([element]))

    result = await books_pipeline.run(page)

    assert result.is_error()
    traversal_error = result.error
    assert isinstance(traversal_error, TraversalItemError)
    assert traversal_error.index == 0
    assert traversal_error.__cause__ is traversal_error.cause

    build_error = traversal_error.cause
    assert isinstance(build_error, BuildFieldError)
    assert build_error.field == "title"
    assert build_error.cause is browser_error
    assert build_error.__cause__ is browser_error
    element.text.assert_not_awaited()
