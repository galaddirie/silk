# pyright: strict
"""Positive typing contracts for named policy composition."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_type

from fp_ops import (
    CollectionOperation,
    Operation,
    Result,
    _,
    build,
    fanout_all_settled,
    fanout_parallel,
    retry,
    traverse,
    traverse_all_settled,
    traverse_lossy,
    traverse_parallel,
)

from silk.actions.navigation import CurrentUrl as current_url, Title as title
from silk.browsers.models import Page


@dataclass(frozen=True, slots=True)
class PageSummary:
    url: str
    title: str


async def exact_policy_operation_types(page: Page) -> None:
    url = current_url(_)
    page_title = title(_)
    assert_type(url, Operation[Page, str])
    assert_type(page_title, Operation[Page, str])

    fields: Mapping[str, Operation[Page, str]] = {
        "url": url,
        "title": page_title,
    }
    assert_type(
        build(fields, PageSummary),
        Operation[Page, PageSummary],
    )
    assert_type(
        retry(url, attempts=3),
        Operation[Page, str],
    )
    assert_type(
        fanout_parallel(url, page_title, limit=2),
        Operation[Page, tuple[str, str]],
    )
    assert_type(
        fanout_all_settled(url, page_title, limit=2),
        Operation[
            Page,
            tuple[Result[str, Exception], Result[str, Exception]],
        ],
    )
    assert_type(
        traverse(url),
        CollectionOperation[Page, str],
    )
    assert_type(
        traverse_parallel(url, limit=2),
        CollectionOperation[Page, str],
    )
    assert_type(
        traverse_all_settled(url, limit=2),
        CollectionOperation[Page, Result[str, Exception]],
    )
    assert_type(
        traverse_lossy(url, limit=2),
        CollectionOperation[Page, str],
    )

    assert_type(
        await build(fields, PageSummary).run(page),
        Result[PageSummary, Exception],
    )
    assert_type(
        await fanout_all_settled(url, page_title).run(page),
        Result[
            tuple[Result[str, Exception], Result[str, Exception]],
            Exception,
        ],
    )
