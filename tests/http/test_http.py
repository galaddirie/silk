"""Contracts for HTTP as an environment capability."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import FrozenInstanceError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock

import httpx
import pytest
from fp_ops import Environment, EnvironmentError, Error, Ok, Result, _, retry

from silk.browsers.models import BrowserContext, BrowserOptions, Page
from silk.browsers.sessions import BrowserSession
from silk.errors import BrowserError, BrowserTimeoutError, UnsupportedOperationError
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

BINARY = bytes(range(256)) * 4


class FakeHttpClient(HttpClient):
    def __init__(self, *outcomes: Result[HttpResponse, Exception]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[HttpRequest] = []

    async def send(self, request: HttpRequest) -> Result[HttpResponse, Exception]:
        self.requests.append(request)
        return self.outcomes.pop(0)


def env(client: HttpClient) -> Environment:
    return Environment().with_value(HTTP, client)


def response(status: int = 200, body: bytes = b"{}", **headers: str) -> HttpResponse:
    return HttpResponse(
        url="https://api.test/x", status=status, headers=headers, body=body
    )


# --- values -----------------------------------------------------------------


def test_request_defaults_and_immutability() -> None:
    params = {"a": "1"}
    headers = {"X-Key": "v"}
    request = HttpRequest("https://api.test/x", "post", params=params, headers=headers)
    params["b"] = "2"
    headers["X-Other"] = "w"

    assert request.method == "POST"
    assert dict(request.params) == {"a": "1"}
    assert dict(request.headers) == {"X-Key": "v"}
    with pytest.raises(FrozenInstanceError):
        request.url = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.headers["X-New"] = "x"  # type: ignore[index]
    assert HttpRequest("https://api.test/x").full_url == "https://api.test/x"


def test_request_rejects_negative_timeout() -> None:
    with pytest.raises(ValueError):
        HttpRequest("https://api.test/x", timeout_ms=-1)


def test_params_are_appended_to_an_existing_query_and_none_is_dropped() -> None:
    request = HttpRequest(
        "https://api.test/search?q=silk&page=2#top",
        params={"limit": 10, "debug": True, "skip": None, "name": "a b&c"},
    )

    assert request.full_url == (
        "https://api.test/search?q=silk&page=2&limit=10&debug=true&name=a+b%26c#top"
    )


def test_empty_params_never_replace_the_query() -> None:
    url = "https://api.test/search?q=silk"
    assert HttpRequest(url).full_url == url
    assert HttpRequest(url, params={"skip": None}).full_url == url
    assert (
        HttpRequest("https://api.test/search", params={"q": "x"}).full_url
        == "https://api.test/search?q=x"
    )


def test_response_headers_are_lower_cased_and_read_only() -> None:
    value = response(**{"Content-Type": "text/plain"})
    assert dict(value.headers) == {"content-type": "text/plain"}
    with pytest.raises(TypeError):
        value.headers["x"] = "y"  # type: ignore[index]


def test_response_text_uses_the_declared_charset() -> None:
    latin = response(body="café".encode("latin-1"))
    assert latin.text() == "caf\ufffd"
    declared = HttpResponse(
        "u",
        200,
        {"Content-Type": 'text/html; charset="ISO-8859-1"'},
        "café".encode("latin-1"),
    )
    assert declared.charset == "ISO-8859-1"
    assert declared.text() == "café"
    unknown = HttpResponse("u", 200, {"content-type": "text/html; charset=nope"}, b"ok")
    assert unknown.text() == "ok"


def test_response_json_parses_or_raises_value_error() -> None:
    assert response(body=b'{"a": [1, 2]}').json() == {"a": [1, 2]}
    latin = HttpResponse(
        "u",
        200,
        {"content-type": "application/json; charset=latin-1"},
        '"café"'.encode("latin-1"),
    )
    assert latin.json() == "café"
    with pytest.raises(ValueError):
        response(body=b"<html>").json()
    with pytest.raises(ValueError):
        response(body=b"\xff\xfe\xfa").json()


def test_status_error_carries_the_response() -> None:
    failed = response(404, b"missing")
    error = HttpStatusError(failed)
    assert isinstance(error, BrowserError)
    assert error.response is failed
    assert error.status == 404
    assert "404" in str(error)


# --- Fetch / FetchJson ------------------------------------------------------


async def test_fetch_sends_a_bare_url_as_get() -> None:
    client = FakeHttpClient(Ok(response()))

    outcome = await Fetch(_).run("https://api.test/x", environment=env(client))

    assert outcome.is_ok()
    assert outcome.ok.status == 200
    assert client.requests == [HttpRequest("https://api.test/x")]


async def test_fetch_passes_request_values_through() -> None:
    client = FakeHttpClient(Ok(response(201)))
    request = HttpRequest("https://api.test/x", "POST", body=b"data")

    outcome = await Fetch(_).run(request, environment=env(client))

    assert outcome.is_ok()
    assert client.requests[0] is request


async def test_fetch_turns_unaccepted_statuses_into_status_errors() -> None:
    failed = response(503, b"busy")
    client = FakeHttpClient(Ok(failed))

    outcome = await Fetch(_).run("https://api.test/x", environment=env(client))

    assert outcome.is_error()
    assert isinstance(outcome.error, HttpStatusError)
    assert outcome.error.response is failed
    assert outcome.error.status == 503


async def test_fetch_ok_status_can_be_overridden() -> None:
    client = FakeHttpClient(Ok(response(404)), Ok(response(200)))
    operation = Fetch(_, ok_status={200, 404})

    first = await operation.run("https://api.test/x", environment=env(client))
    second = await operation.run("https://api.test/x", environment=env(client))

    assert first.is_ok() and first.ok.status == 404
    assert second.is_ok() and second.ok.status == 200
    narrow = await Fetch(_, ok_status={204}).run(
        "https://api.test/x", environment=env(FakeHttpClient(Ok(response(200))))
    )
    assert isinstance(narrow.error, HttpStatusError)


async def test_fetch_passes_transport_errors_through_unchanged() -> None:
    failure = BrowserTimeoutError("slow")
    client = FakeHttpClient(Error(failure))

    outcome = await Fetch(_).run("https://api.test/x", environment=env(client))

    assert outcome.is_error()
    assert outcome.error is failure


def test_fetch_declares_the_http_requirement() -> None:
    assert Fetch(_).required_environment == (HTTP,)
    assert FetchJson(_).required_environment == (HTTP,)


async def test_fetch_without_a_client_fails_preflight() -> None:
    outcome = await Fetch(_).run("https://api.test/x")

    assert outcome.is_error()
    assert isinstance(outcome.error, EnvironmentError)
    assert "http" in str(outcome.error)


async def test_fetch_json_parses_and_composes_with_map() -> None:
    client = FakeHttpClient(Ok(response(body=b'{"id": 7}')))

    outcome = await (
        FetchJson(_)
        .map(lambda data: data["id"] if isinstance(data, dict) else None)
        .run("https://api.test/x", environment=env(client))
    )

    assert outcome.is_ok()
    assert outcome.ok == 7


async def test_fetch_json_reports_invalid_json_and_status_errors() -> None:
    invalid = await FetchJson(_).run(
        "https://api.test/x",
        environment=env(FakeHttpClient(Ok(response(body=b"<html>")))),
    )
    assert isinstance(invalid.error, ValueError)

    failed = await FetchJson(_).run(
        "https://api.test/x",
        environment=env(FakeHttpClient(Ok(response(500)))),
    )
    assert isinstance(failed.error, HttpStatusError)


async def test_retry_on_status_errors_recovers_from_a_503() -> None:
    client = FakeHttpClient(Ok(response(503)), Ok(response(200)))

    outcome = await retry(Fetch(_), attempts=3, on=HttpStatusError).run(
        "https://api.test/x", environment=env(client)
    )

    assert outcome.is_ok()
    assert outcome.ok.status == 200
    assert len(client.requests) == 2


async def test_retry_on_status_errors_leaves_transport_errors_alone() -> None:
    failure = BrowserError("down")
    client = FakeHttpClient(Error(failure), Ok(response(200)))

    outcome = await retry(Fetch(_), attempts=3, on=HttpStatusError).run(
        "https://api.test/x", environment=env(client)
    )

    assert outcome.is_error()
    assert outcome.error is failure
    assert len(client.requests) == 1


# --- optional httpx ---------------------------------------------------------


def test_silk_http_imports_without_httpx() -> None:
    code = (
        "import sys\n"
        "sys.modules['httpx'] = None\n"
        "import silk, silk.http\n"
        "from silk.http import HttpxClient, HttpRequest\n"
        "assert HttpRequest('https://x').full_url == 'https://x'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_no_silk_module_imports_httpx_eagerly() -> None:
    code = (
        "import sys, silk, silk.http, silk.actions, silk.browsers, silk.scraping\n"
        "assert 'httpx' not in sys.modules, 'httpx imported'\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def mock_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


async def test_httpx_client_sends_method_params_headers_and_body() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            201,
            headers=[("Content-Type", "application/json"), ("X-Multi", "a")]
            + [("X-Multi", "b")],
            content=b'{"ok": true}',
        )

    async with mock_client(httpx.MockTransport(handle)) as client:
        outcome = await HttpxClient(client).send(
            HttpRequest(
                "https://api.test/items?q=silk",
                "PUT",
                params={"page": 2, "skip": None},
                headers={"X-Key": "secret"},
                body=b"\x00payload",
            )
        )

    assert outcome.is_ok()
    sent = seen[0]
    assert sent.method == "PUT"
    assert str(sent.url) == "https://api.test/items?q=silk&page=2"
    assert sent.headers["x-key"] == "secret"
    assert sent.content == b"\x00payload"
    assert outcome.ok == HttpResponse(
        "https://api.test/items?q=silk&page=2",
        201,
        {
            "content-type": "application/json",
            "x-multi": "a, b",
            "content-length": "12",
        },
        b'{"ok": true}',
    )


async def test_httpx_client_keeps_the_query_when_params_are_empty() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    async with mock_client(httpx.MockTransport(handle)) as client:
        await HttpxClient(client).send(HttpRequest("https://api.test/x?a=1"))

    assert str(seen[0].url) == "https://api.test/x?a=1"


async def test_httpx_client_follows_redirects_by_default() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(302, headers={"Location": "/new"})
        return httpx.Response(200, content=b"moved")

    async with mock_client(httpx.MockTransport(handle)) as client:
        followed = await HttpxClient(client).send(HttpRequest("https://api.test/old"))
        kept = await HttpxClient(client, follow_redirects=False).send(
            HttpRequest("https://api.test/old")
        )

    assert followed.is_ok() and followed.ok.url == "https://api.test/new"
    assert followed.ok.body == b"moved"
    assert kept.is_ok() and kept.ok.status == 302


async def test_httpx_client_passes_the_timeout_and_translates_timeouts() -> None:
    timeouts: list[object] = []

    def handle(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        raise httpx.ReadTimeout("too slow", request=request)

    async with mock_client(httpx.MockTransport(handle)) as client:
        outcome = await HttpxClient(client).send(
            HttpRequest("https://api.test/x", timeout_ms=250)
        )

    assert timeouts[0] == {"connect": 0.25, "read": 0.25, "write": 0.25, "pool": 0.25}
    assert outcome.is_error()
    assert isinstance(outcome.error, BrowserTimeoutError)
    assert isinstance(outcome.error.__cause__, httpx.ReadTimeout)


async def test_httpx_client_translates_transport_errors() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with mock_client(httpx.MockTransport(handle)) as client:
        outcome = await HttpxClient(client).send(HttpRequest("https://api.test/x"))

    assert outcome.is_error()
    assert type(outcome.error) is BrowserError
    assert isinstance(outcome.error.__cause__, httpx.ConnectError)


async def test_httpx_client_works_as_the_fetch_environment() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"path": request.url.path})

    async with mock_client(httpx.MockTransport(handle)) as client:
        outcome = await FetchJson(_).run(
            "https://api.test/hello", environment=env(HttpxClient(client))
        )

    assert outcome.is_ok()
    assert outcome.ok == {"path": "/hello"}


# --- browser transports -----------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def _reply(
        self,
        status: int,
        body: bytes,
        content_type: str = "text/plain",
        extra: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _handle(self) -> None:
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if path == "/":
            self._reply(200, b"<title>home</title>", "text/html")
        elif path == "/login":
            self._reply(
                200,
                b"<title>logged in</title>",
                "text/html",
                (("Set-Cookie", "session=s3cret; Path=/"),),
            )
        elif path == "/echo":
            payload = {
                "method": self.command,
                "path": self.path,
                "cookie": self.headers.get("Cookie"),
                "x_key": self.headers.get("X-Key"),
                "body": base64.b64encode(body).decode(),
            }
            self._reply(
                200,
                json.dumps(payload).encode(),
                "application/json",
                (("X-Multi", "a"), ("X-Multi", "b")),
            )
        elif path == "/redirect":
            self._reply(302, b"", extra=(("Location", "/echo?from=redirect"),))
        elif path == "/binary":
            self._reply(200, BINARY, "application/octet-stream")
        elif path == "/unavailable":
            self._reply(503, b"try later")
        elif path == "/slow":
            time.sleep(1.5)
            self._reply(200, b"late")
        else:
            self._reply(404, b"not found")

    do_GET = _handle
    do_POST = _handle


@pytest.fixture
def server_url() -> Iterator[str]:
    yield from _serve()


@pytest.fixture
def other_origin_url() -> Iterator[str]:
    yield from _serve()


def _serve() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
async def browser_session() -> AsyncIterator[BrowserSession]:
    options = BrowserOptions(headless=True, timeout=10_000)
    async with BrowserSession(options=options) as session:
        yield session


async def test_context_client_rejects_non_playwright_contexts() -> None:
    context = MagicMock(spec=BrowserContext)

    outcome = await ContextHttpClient(context).send(HttpRequest("http://127.0.0.1/"))

    assert outcome.is_error()
    assert isinstance(outcome.error, UnsupportedOperationError)


async def test_page_client_reports_evaluation_errors() -> None:
    page = MagicMock(spec=Page)
    failure = BrowserError("page closed")

    async def evaluate(script: str, argument: object) -> Result[object, Exception]:
        return Error(failure)

    page.evaluate = evaluate
    outcome = await PageFetchClient(page).send(HttpRequest("http://127.0.0.1/"))
    assert outcome.is_error() and outcome.error is failure

    async def malformed(script: str, argument: object) -> Result[object, Exception]:
        return Ok({"ok": True, "url": 1})

    page.evaluate = malformed
    outcome = await PageFetchClient(page).send(HttpRequest("http://127.0.0.1/"))
    assert isinstance(outcome.error, BrowserError)


@pytest.mark.integration
async def test_context_client_shares_the_context_cookies(
    browser_session: BrowserSession, server_url: str
) -> None:
    navigated = await browser_session.page.navigate(f"{server_url}/login")
    assert navigated.is_ok(), navigated
    client = ContextHttpClient(browser_session.context)

    outcome = await client.send(
        HttpRequest(
            f"{server_url}/echo?a=1",
            "POST",
            params={"b": 2},
            headers={"X-Key": "k"},
            body=BINARY,
        )
    )

    assert outcome.is_ok(), outcome
    echoed = outcome.ok.json()
    assert echoed == {
        "method": "POST",
        "path": "/echo?a=1&b=2",
        "cookie": "session=s3cret",
        "x_key": "k",
        "body": base64.b64encode(BINARY).decode(),
    }
    assert outcome.ok.headers["content-type"] == "application/json"
    assert outcome.ok.headers["x-multi"] == "a, b"


@pytest.mark.integration
async def test_context_client_cookies_flow_back_into_the_context(
    browser_session: BrowserSession, server_url: str
) -> None:
    client = ContextHttpClient(browser_session.context)
    logged_in = await client.send(HttpRequest(f"{server_url}/login"))
    assert logged_in.is_ok(), logged_in

    await browser_session.page.navigate(f"{server_url}/")
    cookie = await browser_session.page.evaluate("document.cookie")
    assert cookie.is_ok() and cookie.ok == "session=s3cret"


@pytest.mark.integration
async def test_context_client_redirects_binary_and_statuses(
    browser_session: BrowserSession, server_url: str
) -> None:
    client = ContextHttpClient(browser_session.context)

    redirected = await client.send(HttpRequest(f"{server_url}/redirect"))
    binary = await client.send(HttpRequest(f"{server_url}/binary"))
    unavailable = await client.send(HttpRequest(f"{server_url}/unavailable"))

    assert redirected.is_ok() and redirected.ok.status == 200
    assert redirected.ok.url == f"{server_url}/echo?from=redirect"
    assert binary.is_ok() and binary.ok.body == BINARY
    assert unavailable.is_ok() and unavailable.ok.status == 503
    assert unavailable.ok.text() == "try later"

    via_fetch = await Fetch(_).run(f"{server_url}/unavailable", environment=env(client))
    assert isinstance(via_fetch.error, HttpStatusError)
    assert via_fetch.error.response.body == b"try later"


@pytest.mark.integration
async def test_context_client_translates_timeouts(
    browser_session: BrowserSession, server_url: str
) -> None:
    client = ContextHttpClient(browser_session.context)

    outcome = await client.send(HttpRequest(f"{server_url}/slow", timeout_ms=200))

    assert outcome.is_error()
    assert isinstance(outcome.error, BrowserTimeoutError)


@pytest.mark.integration
async def test_context_client_reports_closed_contexts_as_errors(
    browser_session: BrowserSession, server_url: str
) -> None:
    created = await browser_session.browser.new_context()
    assert created.is_ok()
    await created.ok.close()

    outcome = await ContextHttpClient(created.ok).send(HttpRequest(server_url))

    assert outcome.is_error()
    assert isinstance(outcome.error, BrowserError)


@pytest.mark.integration
async def test_page_client_fetches_with_the_page_cookies(
    browser_session: BrowserSession, server_url: str
) -> None:
    page = browser_session.page
    assert (await page.navigate(f"{server_url}/login")).is_ok()
    client = PageFetchClient(page)

    posted = await client.send(
        HttpRequest(
            "/echo?a=1",
            "POST",
            params={"b": True},
            headers={"X-Key": "k"},
            body=BINARY,
        )
    )

    assert posted.is_ok(), posted
    assert posted.ok.url == f"{server_url}/echo?a=1&b=true"
    assert posted.ok.json() == {
        "method": "POST",
        "path": "/echo?a=1&b=true",
        "cookie": "session=s3cret",
        "x_key": "k",
        "body": base64.b64encode(BINARY).decode(),
    }
    assert posted.ok.headers["x-multi"] == "a, b"


@pytest.mark.integration
async def test_page_client_redirects_binary_and_statuses(
    browser_session: BrowserSession, server_url: str
) -> None:
    assert (await browser_session.page.navigate(f"{server_url}/")).is_ok()
    client = PageFetchClient(browser_session.page)

    redirected = await client.send(HttpRequest(f"{server_url}/redirect"))
    binary = await client.send(HttpRequest(f"{server_url}/binary"))
    unavailable = await client.send(HttpRequest(f"{server_url}/unavailable"))

    assert redirected.is_ok() and redirected.ok.url == (
        f"{server_url}/echo?from=redirect"
    )
    assert binary.is_ok() and binary.ok.body == BINARY
    assert unavailable.is_ok() and unavailable.ok.status == 503

    retried = await retry(Fetch(_), attempts=2, on=HttpStatusError).run(
        f"{server_url}/unavailable", environment=env(client)
    )
    assert isinstance(retried.error, HttpStatusError)


@pytest.mark.integration
async def test_page_client_reports_timeouts_and_cors_failures(
    browser_session: BrowserSession, server_url: str, other_origin_url: str
) -> None:
    assert (await browser_session.page.navigate(f"{server_url}/")).is_ok()
    client = PageFetchClient(browser_session.page)

    slow = await client.send(HttpRequest(f"{server_url}/slow", timeout_ms=200))
    cross_origin = await client.send(HttpRequest(f"{other_origin_url}/echo"))

    assert slow.is_error() and isinstance(slow.error, BrowserTimeoutError)
    assert cross_origin.is_error()
    assert type(cross_origin.error) is BrowserError
    assert "page fetch failed" in str(cross_origin.error)
