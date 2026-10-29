# pyright: strict
"""HTTP requests as an environment capability.

Pipelines fetch with :data:`Fetch` / :data:`FetchJson`; *how* the request is
sent is a dependency provided under :data:`HTTP`::

    from fp_ops import Environment, _

    from silk.http import HTTP, FetchJson, HttpxClient

    async with httpx.AsyncClient() as client:
        result = await FetchJson(_).map(Model.model_validate).run(
            "https://api.example.com/items",
            environment=Environment().with_value(HTTP, HttpxClient(client)),
        )

Three transports ship with Silk:

* :class:`HttpxClient`: a plain ``httpx.AsyncClient`` (``httpx`` is optional);
* :class:`ContextHttpClient`: the browser context's request API, sharing its
  cookies;
* :class:`PageFetchClient`: ``fetch()`` inside a live page, with the browser's
  TLS fingerprint, headers and cookies (and its CORS rules).
"""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from collections.abc import Container, Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

from fp_ops import EnvKey, Error, Ok, Result, environment_result_operation_template

from silk.browsers.drivers.playwright import PlaywrightBrowserContext, translate_error
from silk.browsers.models import BrowserContext, Page
from silk.errors import BrowserError, BrowserTimeoutError, UnsupportedOperationError

if TYPE_CHECKING:
    import httpx

ParamValue = str | int | float | bool | None
_EMPTY_PARAMS: Mapping[str, ParamValue] = MappingProxyType({})
_EMPTY_HEADERS: Mapping[str, str] = MappingProxyType({})
_SUCCESS = range(200, 300)


def _param_text(value: str | int | float | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """One HTTP request; mappings are copied into read-only views.

    ``params`` are appended to any query string already in ``url`` (never
    replacing it); ``None`` values are dropped and booleans are sent as
    ``true``/``false``. ``timeout_ms=None`` uses the transport's default.
    """

    url: str
    method: str = "GET"
    params: Mapping[str, ParamValue] = field(default=_EMPTY_PARAMS)
    headers: Mapping[str, str] = field(default=_EMPTY_HEADERS)
    body: bytes | None = None
    timeout_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.method:
            raise ValueError("method must not be empty")
        if self.timeout_ms is not None and self.timeout_ms < 0:
            raise ValueError("timeout_ms must be non-negative")
        object.__setattr__(self, "method", self.method.upper())
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @property
    def full_url(self) -> str:
        """``url`` with ``params`` appended to its query string."""

        pairs = [
            (name, _param_text(value))
            for name, value in self.params.items()
            if value is not None
        ]
        if not pairs:
            return self.url
        parts = urlsplit(self.url)
        extra = urlencode(pairs)
        query = f"{parts.query}&{extra}" if parts.query else extra
        return urlunsplit(parts._replace(query=query))


def _charset(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    for parameter in content_type.split(";")[1:]:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "charset":
            charset = value.strip().strip("\"'")
            return charset or None
    return None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """A complete response; ``url`` is the final URL after redirects.

    Header names are lower-cased; repeated headers are joined with ``", "``.
    """

    url: str
    status: int
    headers: Mapping[str, str] = field(default=_EMPTY_HEADERS)
    body: bytes = b""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "headers",
            MappingProxyType(
                {name.lower(): value for name, value in self.headers.items()}
            ),
        )

    @property
    def charset(self) -> str | None:
        """The ``charset`` parameter of ``content-type``, if any."""

        return _charset(self.headers.get("content-type"))

    def text(self) -> str:
        """The body decoded with the declared charset (default UTF-8).

        Undecodable bytes become U+FFFD; an unknown charset falls back to UTF-8.
        """

        charset = self.charset or "utf-8"
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")

    def json(self) -> object:
        """The body parsed as JSON; raises :class:`ValueError` if it is not."""

        charset = self.charset
        if charset is None:
            return json.loads(self.body)
        try:
            decoded = self.body.decode(charset)
        except LookupError as error:
            raise ValueError(f"unknown response charset {charset!r}") from error
        return json.loads(decoded)


def _joined_headers(pairs: Iterable[tuple[str, str]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for name, value in pairs:
        key = name.lower()
        headers[key] = f"{headers[key]}, {value}" if key in headers else value
    return headers


class HttpStatusError(BrowserError):
    """A response arrived with a status outside the accepted ones."""

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.status = response.status
        super().__init__(f"HTTP {response.status} for {response.url}")


class HttpClient(ABC):
    """Sends :class:`HttpRequest` values; provided to pipelines under :data:`HTTP`."""

    @abstractmethod
    async def send(self, request: HttpRequest) -> Result[HttpResponse, Exception]:
        """Send ``request``. Every status is ``Ok``; failures are ``Error`` values."""

        ...


HTTP = EnvKey("http", HttpClient)  # type: ignore[type-abstract]
"""Environment key for the :class:`HttpClient` that ``Fetch`` uses."""


def _as_request(request: HttpRequest | str) -> HttpRequest:
    return HttpRequest(request) if isinstance(request, str) else request


async def _fetch(
    request: HttpRequest | str,
    http: HttpClient,
    ok_status: Container[int],
) -> Result[HttpResponse, Exception]:
    sent = await http.send(_as_request(request))
    if sent.is_error():
        return Error(sent.error)
    response = sent.ok
    if response.status not in ok_status:
        return Error(HttpStatusError(response))
    return Ok(response)


@environment_result_operation_template(HTTP)
async def Fetch(
    request: HttpRequest | str,
    http: HttpClient,
    *,
    ok_status: Container[int] = _SUCCESS,
) -> Result[HttpResponse, Exception]:
    """Send a request (a bare URL is a ``GET``) with the environment's client.

    A status outside ``ok_status`` is an ``Error(HttpStatusError)`` that keeps
    the response.
    """

    return await _fetch(request, http, ok_status)


@environment_result_operation_template(HTTP)
async def FetchJson(
    request: HttpRequest | str,
    http: HttpClient,
    *,
    ok_status: Container[int] = _SUCCESS,
) -> Result[object, Exception]:
    """Like :data:`Fetch`, then parse the body as JSON (``ValueError`` if invalid).

    Validate the result by mapping, e.g. ``FetchJson(_).map(Model.model_validate)``.
    """

    fetched = await _fetch(request, http, ok_status)
    if fetched.is_error():
        return Error(fetched.error)
    try:
        return Ok(fetched.ok.json())
    except ValueError as error:
        return Error(error)


class ContextHttpClient(HttpClient):
    """Send through a Playwright browser context's request API.

    Requests share the context's cookie jar both ways and follow redirects;
    they are not subject to CORS and do not run page scripts. Only contexts
    created by :class:`~silk.browsers.drivers.PlaywrightDriver` are supported;
    others yield ``Error(UnsupportedOperationError)``.
    """

    def __init__(self, context: BrowserContext) -> None:
        self._context = context

    async def send(self, request: HttpRequest) -> Result[HttpResponse, Exception]:
        context = self._context
        if not isinstance(context, PlaywrightBrowserContext):
            return Error(
                UnsupportedOperationError(
                    "ContextHttpClient needs a Playwright browser context, "
                    f"got {type(context).__name__}"
                )
            )
        try:
            native = await context.native.request.fetch(
                request.full_url,
                method=request.method,
                headers=dict(request.headers),
                data=request.body,
                timeout=request.timeout_ms,
                fail_on_status_code=False,
            )
            try:
                body = await native.body()
                return Ok(
                    HttpResponse(
                        url=native.url,
                        status=native.status,
                        headers=_joined_headers(
                            (header["name"], header["value"])
                            for header in native.headers_array
                        ),
                        body=body,
                    )
                )
            finally:
                await native.dispose()
        except Exception as error:
            return Error(translate_error(error))


_PAGE_FETCH_SCRIPT = """
async (request) => {
  const init = { method: request.method, headers: request.headers, credentials: "include" };
  if (request.body !== null) {
    init.body = Uint8Array.from(atob(request.body), (c) => c.charCodeAt(0));
  }
  if (request.timeoutMs !== null) {
    init.signal = AbortSignal.timeout(request.timeoutMs);
  }
  try {
    const response = await fetch(request.url, init);
    const bytes = new Uint8Array(await response.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i += 0x8000) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    const headers = [];
    response.headers.forEach((value, name) => headers.push([name, value]));
    return { ok: true, url: response.url, status: response.status, headers, body: btoa(binary) };
  } catch (error) {
    const name = error && error.name ? String(error.name) : "Error";
    const message = error && error.message ? String(error.message) : String(error);
    return { ok: false, name, message };
  }
}
"""


def _page_fetch_response(value: object) -> Result[HttpResponse, Exception]:
    if not isinstance(value, dict):
        return Error(BrowserError(f"unexpected page fetch result: {value!r}"))
    outcome = cast(dict[str, object], value)
    if outcome.get("ok") is not True:
        name = str(outcome.get("name"))
        message = f"page fetch failed: {name}: {outcome.get('message')}"
        if name == "TimeoutError":
            return Error(BrowserTimeoutError(message))
        return Error(BrowserError(message))
    url, status = outcome.get("url"), outcome.get("status")
    headers, body = outcome.get("headers"), outcome.get("body")
    if (
        not isinstance(url, str)
        or not isinstance(status, int)
        or not isinstance(headers, list)
        or not isinstance(body, str)
    ):
        return Error(BrowserError(f"malformed page fetch result: {outcome!r}"))
    pairs: list[tuple[str, str]] = []
    for pair in cast(list[object], headers):
        if not isinstance(pair, list) or len(cast(list[object], pair)) != 2:
            return Error(BrowserError(f"malformed page fetch header: {pair!r}"))
        header_name, header_value = cast(list[object], pair)
        pairs.append((str(header_name), str(header_value)))
    return Ok(
        HttpResponse(
            url=url,
            status=status,
            headers=_joined_headers(pairs),
            body=base64.b64decode(body),
        )
    )


class PageFetchClient(HttpClient):
    """Send with ``fetch()`` inside a live page (``credentials: "include"``).

    The request uses the browser's network stack, TLS fingerprint, cookies and
    default headers, so it passes bot checks that plain clients fail. Browser
    rules apply: cross-origin requests need CORS, relative URLs resolve
    against the page, forbidden headers (``Cookie``, ``User-Agent``...) are
    dropped, and ``Set-Cookie`` is never visible. Network and CORS failures
    are ``BrowserError``; a timeout is ``BrowserTimeoutError``.
    """

    def __init__(self, page: Page) -> None:
        self._page = page

    async def send(self, request: HttpRequest) -> Result[HttpResponse, Exception]:
        argument: dict[str, object] = {
            "url": request.full_url,
            "method": request.method,
            "headers": dict(request.headers),
            "body": (
                None
                if request.body is None
                else base64.b64encode(request.body).decode("ascii")
            ),
            "timeoutMs": request.timeout_ms,
        }
        try:
            evaluated = await self._page.evaluate(_PAGE_FETCH_SCRIPT, argument)
        except Exception as error:
            return Error(translate_error(error))
        if evaluated.is_error():
            return Error(translate_error(evaluated.error))
        try:
            return _page_fetch_response(evaluated.ok)
        except Exception as error:
            return Error(BrowserError(f"malformed page fetch result: {error}"))


def _translate_httpx_error(error: Exception) -> Exception:
    if not type(error).__module__.startswith("httpx"):
        return error
    import httpx

    translated: BrowserError
    if isinstance(error, httpx.TimeoutException):
        translated = BrowserTimeoutError(str(error) or type(error).__name__)
    else:
        translated = BrowserError(str(error) or type(error).__name__)
    translated.__cause__ = error
    return translated


class HttpxClient(HttpClient):
    """Send with an ``httpx.AsyncClient`` the caller owns (and closes).

    Requires the optional ``httpx`` package. Redirects are followed unless
    ``follow_redirects=False``, matching the browser transports. httpx
    failures become ``BrowserError`` (timeouts ``BrowserTimeoutError``) with the
    httpx error as ``__cause__``.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        follow_redirects: bool = True,
    ) -> None:
        self._client = client
        self._follow_redirects = follow_redirects

    async def send(self, request: HttpRequest) -> Result[HttpResponse, Exception]:
        try:
            if request.timeout_ms is None:
                native = self._client.build_request(
                    request.method,
                    request.full_url,
                    headers=dict(request.headers),
                    content=request.body,
                )
            else:
                native = self._client.build_request(
                    request.method,
                    request.full_url,
                    headers=dict(request.headers),
                    content=request.body,
                    timeout=request.timeout_ms / 1000,
                )
            response = await self._client.send(
                native, follow_redirects=self._follow_redirects
            )
            return Ok(
                HttpResponse(
                    url=str(response.url),
                    status=response.status_code,
                    headers=_joined_headers(response.headers.multi_items()),
                    body=response.content,
                )
            )
        except Exception as error:
            return Error(_translate_httpx_error(error))


__all__ = [
    "HTTP",
    "ContextHttpClient",
    "Fetch",
    "FetchJson",
    "HttpClient",
    "HttpRequest",
    "HttpResponse",
    "HttpStatusError",
    "HttpxClient",
    "PageFetchClient",
    "ParamValue",
]
