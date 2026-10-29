# pyright: strict
"""Positive typing contracts for HTTP fetch templates and clients."""

from typing import assert_type

import httpx
from fp_ops import Environment, Operation, Result, _, from_environment, provide, retry

from silk.browsers.models import CONTEXT, BrowserContext, Page
from silk.errors import BrowserError
from silk.http import (
    HTTP,
    ContextHttpClient,
    Fetch,
    FetchJson,
    HttpClient,
    HttpRequest,
    HttpResponse,
    HttpStatusError,
    HttpxClient,
    PageFetchClient,
)


def item_id(data: object) -> int:
    if isinstance(data, int):
        return data
    raise ValueError("no id")


def templates() -> None:
    assert_type(Fetch(_), Operation[HttpRequest | str, HttpResponse])
    assert_type(
        Fetch(_, ok_status=range(200, 400)),
        Operation[HttpRequest | str, HttpResponse],
    )
    assert_type(
        Fetch(_, ok_status={200, 404}), Operation[HttpRequest | str, HttpResponse]
    )
    assert_type(FetchJson(_), Operation[HttpRequest | str, object])
    assert_type(FetchJson(_).map(item_id), Operation[HttpRequest | str, int])

    resilient = retry(Fetch(_), attempts=3, on=HttpStatusError)
    assert_type(resilient, Operation[HttpRequest | str, HttpResponse])


def chained(urls: Operation[int, str], requests: Operation[int, HttpRequest]) -> None:
    assert_type(urls.then(Fetch(_)), Operation[int, HttpResponse])
    assert_type(requests.then(FetchJson(_)), Operation[int, object])


def clients(context: BrowserContext, page: Page, client: httpx.AsyncClient) -> None:
    transports: list[HttpClient] = [
        ContextHttpClient(context),
        PageFetchClient(page),
        HttpxClient(client),
        HttpxClient(client, follow_redirects=False),
    ]
    environment = Environment().with_value(HTTP, transports[0])
    assert_type(environment, Environment)

    via_context = provide(
        HTTP,
        from_environment(CONTEXT).map(ContextHttpClient),
        FetchJson(_),
    )
    assert_type(via_context, Operation[HttpRequest | str, object])


async def values(client: HttpClient) -> None:
    request = HttpRequest(
        "https://api.example.com/items?q=a",
        "POST",
        params={"page": 2, "debug": True, "skip": None, "ratio": 0.5},
        headers={"Accept": "application/json"},
        body=b"{}",
        timeout_ms=5_000,
    )
    assert_type(request.full_url, str)
    sent = await client.send(request)
    assert_type(sent, Result[HttpResponse, Exception])
    if sent.is_ok():
        response = sent.ok
        assert_type(response.status, int)
        assert_type(response.text(), str)
        assert_type(response.json(), object)
        assert_type(response.headers.get("content-type"), str | None)

    error = HttpStatusError(HttpResponse("https://x", 500, {}, b""))
    assert_type(error.response, HttpResponse)
    assert_type(error.status, int)
    browser_error: BrowserError = error
    assert isinstance(browser_error, BrowserError)


# A bare URL or a full request can be the operation's input.
by_url: Operation[str, HttpResponse] = Fetch(_)
by_request: Operation[HttpRequest, HttpResponse] = Fetch(_)
