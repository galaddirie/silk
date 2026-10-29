"""Parity: one Silk pipeline, run on a static page and on live Chromium.

Every test serves the same HTML from a local HTTP server, so the live page and
the static page share a URL, and asserts the two backends answer identically.

``inner_text`` is an approximation on the static backend (no CSS layout). It
is compared here only on markup whose rendering follows from tag names alone;
stylesheet-driven layout (``display`` from CSS rules, ``visibility``,
``text-transform``, generated content) is an intentional exemption.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fp_ops import Operation, _, build, traverse

from silk.actions.elements import (
    ElementExists,
    ExtractTable,
    GetAttribute,
    GetInnerText,
    GetText,
    GetUrl,
    Query,
    QueryAll,
    RequireAttribute,
    WaitForElement,
    optional,
)
from silk.actions.navigation import Navigate
from silk.browsers.models import BrowserOptions, ElementHandle, Page
from silk.browsers.sessions import BrowserSession
from silk.selectors import SELF, SelectorGroup, css, xpath
from silk.static import SnapshotElement, SnapshotPage, StaticElement, StaticPage

FIXTURE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>  Parity   Shop </title>
</head>
<body>
  <h1>  The   Shop </h1>
  <section class="catalog">
    <article class="product_pod" data-sku="a1">
      <h3><a href="catalogue/alpha/index.html" title="Alpha &amp; Co">Alpha…</a></h3>
      <p class="price_color">£10.00</p>
      <p class="desc">First
         line<br>second   line</p>
      <span class="badge"> New </span>
    </article>
    <article class="product_pod" data-sku="b2">
      <h3><a href="/catalogue/beta/" title="Beta">Beta</a></h3>
      <p class="price_color">£20.00</p>
      <p class="desc">Only <em>one</em> line</p>
    </article>
    <article class="product_pod" data-sku="c3">
      <h3><a href="//cdn.example.com/gamma" title="Gamma">Gamma</a></h3>
      <p class="sale">£5.00</p>
    </article>
  </section>
  <ul class="tags"><li>one</li><li>two <em>em</em></li></ul>
  <table id="stock">
    <tr><th>Name</th><th>Qty</th></tr>
    <tr><td> Alpha </td><td>1</td></tr>
    <tr><td>Beta</td><td>2</td></tr>
  </table>
  <pre>
  pre   text
end</pre>
  <div id="mixed">inline <span>span</span> text<div>block</div>tail <b>bold</b><script>ignored()</script></div>
</body>
</html>
"""

BASE_FIXTURE = """<html><head><base href="/other/dir/"></head>
<body><a id="rel" href="page.html">x</a><a id="abs" href="/root">y</a></body></html>
"""

PATH = "/shop/index.html"


@dataclass(frozen=True, slots=True)
class Book:
    sku: str | None
    title: str
    price: str
    url: str
    badge: str | None
    description: str | None


price = SelectorGroup(
    "price",
    css("p.price_color"),
    xpath("//p[contains(@class, 'sale')]"),
)

extract_book = build(
    {
        "sku": GetAttribute(SELF, _, attribute="data-sku"),
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText(price, _),
        "url": GetUrl(xpath("//h3/a"), _),
        "badge": optional(GetText(".badge", _)),
        "description": optional(GetInnerText("p.desc", _)),
    },
    Book,
)

books: Operation[Page, list[Book]] = QueryAll("article.product_pod", _) >> traverse(
    extract_book
)


async def serve(documents: dict[str, str]) -> asyncio.Server:
    async def respond(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            path = request.split(b" ", 2)[1].decode()
            document = documents.get(path)
            status = b"200 OK" if document is not None else b"404 Not Found"
            body = (document or "").encode()
            writer.write(
                b"HTTP/1.1 "
                + status
                + b"\r\nContent-Type: text/html; charset=utf-8\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    return await asyncio.start_server(respond, "127.0.0.1", 0)


@dataclass(frozen=True, slots=True)
class Pair:
    live: Page
    static: StaticPage


@pytest.fixture
async def session() -> AsyncIterator[BrowserSession]:
    async with BrowserSession(
        options=BrowserOptions(headless=True, timeout=10_000)
    ) as browser_session:
        yield browser_session


@pytest.fixture
async def open_pair(
    session: BrowserSession,
) -> AsyncIterator[Callable[[str], Awaitable[Pair]]]:
    documents: dict[str, str] = {}
    server = await serve(documents)
    port = server.sockets[0].getsockname()[1]

    async def load(html: str) -> Pair:
        documents[PATH] = html
        url = f"http://127.0.0.1:{port}{PATH}"
        navigated = await Navigate(_, url).run(session.page)
        assert navigated.is_ok(), navigated
        return Pair(session.page, StaticPage.from_html(html, url=url))

    try:
        yield load
    finally:
        server.close()
        await server.wait_closed()


async def run_both(pair: Pair, operation: Operation[Page, Any]) -> tuple[Any, Any]:
    live = await operation.run(pair.live)
    static = await operation.run(pair.static)
    assert live.is_ok(), live
    assert static.is_ok(), static
    return live.ok, static.ok


pytestmark = pytest.mark.integration


async def test_extraction_pipeline_parity(
    open_pair: Callable[[str], Awaitable[Pair]],
) -> None:
    pair = await open_pair(FIXTURE)
    live, static = await run_both(pair, books)
    assert live == static
    assert [book.sku for book in static] == ["a1", "b2", "c3"]
    assert static[0].url.endswith("/shop/catalogue/alpha/index.html")
    assert static[2].price == "£5.00"


async def test_read_parity(open_pair: Callable[[str], Awaitable[Pair]]) -> None:
    pair = await open_pair(FIXTURE)
    reads = build(
        {
            "h1": GetText("h1", _),
            "body_text": GetText("body", _),
            "body_inner": GetInnerText("body", _),
            "mixed": GetInnerText("#mixed", _),
            "tags": GetInnerText("ul.tags", _),
            "pre": GetText("pre", _),
            "pre_inner": GetInnerText("pre", _),
            "table": ExtractTable("#stock", _),
            "rows": QueryAll("table > tbody > tr", _)
            >> traverse(GetInnerText(SELF, _)),
            "missing": optional(GetText(".nope", _)),
            "exists": ElementExists(css("ul.tags li"), _),
            "relative_xpath": Query("article", _)
            >> GetText(xpath("//p[@class='price_color']"), _),
        }
    )
    live, static = await run_both(pair, reads)
    assert live == static
    assert static["table"] == [
        {"Name": "Alpha", "Qty": "1"},
        {"Name": "Beta", "Qty": "2"},
    ]


async def test_page_metadata_parity(
    open_pair: Callable[[str], Awaitable[Pair]],
) -> None:
    pair = await open_pair(BASE_FIXTURE)
    for read in ("url", "base_url", "title"):
        live = await getattr(pair.live, read)()
        static = await getattr(pair.static, read)()
        assert live.ok == static.ok, read
    urls = build({"rel": GetUrl("#rel", _), "abs": GetUrl("#abs", _)})
    live, static = await run_both(pair, urls)
    assert live == static
    assert static["rel"].endswith("/other/dir/page.html")


async def test_wait_for_element_parity(
    open_pair: Callable[[str], Awaitable[Pair]],
) -> None:
    pair = await open_pair(FIXTURE)
    group = SelectorGroup("g", css(".missing"), css("span.badge"))
    wait = WaitForElement(group, _) >> GetText(SELF, _)
    live, static = await run_both(pair, wait)
    assert live == static == " New "


async def test_snapshot_of_a_live_page(
    open_pair: Callable[[str], Awaitable[Pair]],
) -> None:
    pair = await open_pair(FIXTURE)
    snapshot = await SnapshotPage(_).run(pair.live)
    assert snapshot.is_ok(), snapshot
    assert (await snapshot.ok.url()).ok == (await pair.live.url()).ok
    assert (await snapshot.ok.base_url()).ok == (await pair.live.base_url()).ok

    from_snapshot = await (SnapshotPage(_) >> books).run(pair.live)
    from_live = await books.run(pair.live)
    assert from_snapshot.ok == from_live.ok


async def test_snapshot_of_live_elements(
    open_pair: Callable[[str], Awaitable[Pair]],
) -> None:
    pair = await open_pair(FIXTURE)
    per_element = QueryAll("article.product_pod", _) >> traverse(
        SnapshotElement(_) >> extract_book
    )
    from_snapshots = await per_element.run(pair.live)
    from_live = await books.run(pair.live)
    assert from_snapshots.is_ok(), from_snapshots
    assert from_snapshots.ok == from_live.ok

    table = await Query("#stock", _).run(pair.live)
    assert table.is_ok() and table.ok is not None
    live_table: ElementHandle = table.ok
    snapshot = await SnapshotElement(_).run(live_table)
    assert isinstance(snapshot.ok, StaticElement)
    rows = await ExtractTable(SELF, _).run(snapshot.ok)
    assert rows.ok == (await ExtractTable(SELF, _).run(live_table)).ok
