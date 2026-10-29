"""Unit contracts for the static-HTML backend in ``silk.static``."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import BuildFieldError, Error, Ok, _, build, traverse

from silk.actions.elements import (
    ElementExists,
    ExtractTable,
    GetAttribute,
    GetHtml,
    GetInnerText,
    GetText,
    GetUrl,
    OwnerPage,
    Query,
    QueryAll,
    RequireAttribute,
    WaitForElement,
    WaitOptions,
    optional,
)
from silk.browsers.models import ElementHandle, Page
from silk.errors import (
    BrowserError,
    BrowserTimeoutError,
    ElementNotFoundError,
    UnsupportedOperationError,
)
from silk.selectors import SELF, Selector, SelectorGroup, SelectorType, css, text, xpath
from silk.static import (
    STATIC_CONTEXT_ID,
    HtmlDocument,
    ParseHtml,
    SnapshotElement,
    SnapshotPage,
    StaticElement,
    StaticPage,
    decode_body,
)

URL = "https://example.com/shop/index.html"

DOCUMENT = """<!DOCTYPE html>
<html>
<head><title>  The
  Shop </title></head>
<body>
  <section id="catalog" class="catalog">
    <article class="product featured" data-sku="a1">
      <h3><a href="items/a1.html" title="Alpha">Alpha &amp; Co</a></h3>
      <p class="price">10.00</p>
      <span class="badge">new</span>
      <input name="qty" value="1">
    </article>
    <article class="product" data-sku="b2">
      <h3><a href="/b2" title="Beta">Beta</a></h3>
      <p class="price">20.00</p>
    </article>
  </section>
  <table id="stock">
    <tr><th>Name</th><th>Qty</th></tr>
    <tr><td> Alpha </td><td>1</td></tr>
    <tr><td>Beta</td><td>2</td></tr>
  </table>
  <!-- a comment -->
  <script>window.ignored = true;</script>
</body>
</html>"""


@pytest.fixture
def page() -> StaticPage:
    return StaticPage.from_html(DOCUMENT, url=URL)


async def first(page: StaticPage, selector: str) -> ElementHandle:
    found = await page.query_selector(selector)
    assert found.is_ok() and found.ok is not None, found
    return found.ok


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------


async def test_page_identity_and_metadata(page: StaticPage) -> None:
    assert (await page.url()).ok == URL
    assert (await page.base_url()).ok == URL
    assert (await page.title()).ok == "The Shop"
    assert page.context_id == STATIC_CONTEXT_ID == "static"
    other = StaticPage.from_html(DOCUMENT, url=URL)
    assert page.page_id != other.page_id
    assert (await page.close()).is_ok()


async def test_content_serializes_the_document(page: StaticPage) -> None:
    content = (await page.content()).ok
    assert content.startswith("<!DOCTYPE html>")
    assert '<article class="product featured" data-sku="a1">' in content
    reparsed = StaticPage.from_html(content, url=URL)
    assert len((await reparsed.query_selector_all("article")).ok) == 2


async def test_content_has_no_doctype_when_the_source_had_none() -> None:
    page = StaticPage.from_html("<p>x</p>", url=URL)
    content = (await page.content()).ok
    assert content.startswith("<html>")
    assert "<body><p>x</p></body>" in content


async def test_empty_and_declared_documents_parse() -> None:
    empty = StaticPage.from_html("", url=URL)
    assert (await empty.query_selector("body")).ok is not None
    assert (await empty.title()).ok == ""
    declared = StaticPage.from_html(
        "<?xml version='1.0' encoding='utf-8'?><p>x</p>", url=URL
    )
    assert (await GetText("p", _).run(declared)).ok == "x"


async def test_base_url_honours_base_href_resolved_against_the_url() -> None:
    page = StaticPage.from_html(
        '<head><base href="../catalog/"></head><a href="item.html">x</a>',
        url="https://example.com/shop/index.html",
    )
    assert (await page.base_url()).ok == "https://example.com/catalog/"
    assert (await GetUrl("a", _).run(page)).ok == (
        "https://example.com/catalog/item.html"
    )


async def test_base_url_override_wins_over_base_href() -> None:
    page = StaticPage.from_html(
        '<base href="/ignored/"><a href="x">x</a>',
        url="https://example.com/a",
        base_url="https://cdn.example.com/b/",
    )
    assert (await page.base_url()).ok == "https://cdn.example.com/b/"
    assert (await GetUrl("a", _).run(page)).ok == "https://cdn.example.com/b/x"


async def test_get_url_resolves_relative_absolute_and_protocol_relative_links() -> None:
    page = StaticPage.from_html(
        '<a id="r" href=" items/1 "></a><a id="a" href="/root"></a>'
        '<a id="p" href="//cdn.example.com/x"></a><a id="none"></a>',
        url=URL,
    )
    assert (await GetUrl("#r", _).run(page)).ok == ("https://example.com/shop/items/1")
    assert (await GetUrl("#a", _).run(page)).ok == "https://example.com/root"
    assert (await GetUrl("#p", _).run(page)).ok == "https://cdn.example.com/x"
    missing = await GetUrl("#none", _).run(page)
    assert missing.is_error()
    assert (await optional(GetUrl("#none", _)).run(page)).ok is None


async def test_page_unsupported_operations(page: StaticPage) -> None:
    results = [
        await page.navigate("https://example.com"),
        await page.reload(),
        await page.go_back(),
        await page.go_forward(),
        await page.wait_for_navigation(),
        await page.evaluate("1 + 1"),
        await page.evaluate("x => x", 1),
        await page.screenshot(),
        await page.screenshot(Path("shot.png")),
        await page.mouse_move(1, 2),
        await page.mouse_down(),
        await page.mouse_up(),
        await page.key_press("Enter"),
        await page.key_down("Shift"),
        await page.key_up("Shift"),
        await page.scroll(y=100),
    ]
    for result in results:
        assert result.is_error()
        assert isinstance(result.error, UnsupportedOperationError)
        assert isinstance(result.error, BrowserError)


async def test_wait_for_selector_resolves_immediately(page: StaticPage) -> None:
    visible = await page.wait_for_selector("article", state="visible")
    assert visible.is_ok() and isinstance(visible.ok, StaticElement)
    attached = await page.wait_for_selector("article", state="attached")
    assert attached.is_ok() and attached.ok is not None

    absent = await page.wait_for_selector(".missing", timeout_ms=60_000)
    assert absent.is_error() and isinstance(absent.error, BrowserTimeoutError)

    assert (await page.wait_for_selector(".missing", state="hidden")).ok is None
    assert (await page.wait_for_selector(".missing", state="detached")).ok is None
    present = await page.wait_for_selector("article", state="detached")
    assert present.is_error() and isinstance(present.error, BrowserTimeoutError)
    present = await page.wait_for_selector("article", state="hidden")
    assert present.is_error() and isinstance(present.error, BrowserTimeoutError)


async def test_root_is_the_document_element(page: StaticPage) -> None:
    root = page.root
    assert root.tag == "html"
    assert root.selector is None
    assert (await GetAttribute(SELF, _, attribute="lang").run(root)).ok is None


# --------------------------------------------------------------------------
# Element reads
# --------------------------------------------------------------------------


async def test_element_identity(page: StaticPage) -> None:
    article = await first(page, "article")
    assert isinstance(article, StaticElement)
    assert article.page is page
    assert article.page_id == page.page_id
    assert article.context_id == "static"
    assert article.selector == "article"
    nested = (await article.query_selector("a")).ok
    assert nested is not None and nested.selector == "a"
    assert (await OwnerPage(_).run(article)).ok is page
    assert (await article.content_frame()).ok is None


async def test_text_is_text_content(page: StaticPage) -> None:
    anchor = await first(page, "h3 a")
    assert (await anchor.text()).ok == "Alpha & Co"
    body = await first(page, "body")
    body_text = (await body.text()).ok
    assert "window.ignored = true;" in body_text
    assert "a comment" not in body_text
    price = await first(page, ".price")
    assert (await price.text()).ok == "10.00"


async def test_html_outer_and_inner(page: StaticPage) -> None:
    heading = await first(page, "h3")
    outer = (await heading.html()).ok
    inner = (await heading.html(outer=False)).ok
    assert outer == (
        '<h3><a href="items/a1.html" title="Alpha">Alpha &amp; Co</a></h3>'
    )
    assert inner == '<a href="items/a1.html" title="Alpha">Alpha &amp; Co</a>'
    anchor = await first(page, "h3 a")
    assert (await anchor.html(outer=False)).ok == "Alpha &amp; Co"
    assert (await GetHtml("h3", _).run(page)).ok == outer


async def test_attribute_reads(page: StaticPage) -> None:
    article = await first(page, "article")
    assert (await article.attribute("data-sku")).ok == "a1"
    assert (await article.attribute("DATA-SKU")).ok == "a1"
    assert (await article.attribute("missing")).ok is None
    assert (await GetAttribute("a", _, attribute="title").run(article)).ok == "Alpha"
    missing = await RequireAttribute("a", _, attribute="rel").run(article)
    assert missing.is_error()


async def test_element_interactions_are_unsupported(page: StaticPage) -> None:
    article = await first(page, "article")
    other = await first(page, "table")
    results = [
        await article.click(),
        await article.double_click(),
        await article.fill("x"),
        await article.type("x"),
        await article.select(value="x"),
        await article.scroll_into_view(),
        await article.move_pointer_to(),
        await article.drag_to(other),
    ]
    for result in results:
        assert result.is_error()
        assert isinstance(result.error, UnsupportedOperationError)


async def test_inner_text_approximates_rendered_text() -> None:
    page = StaticPage.from_html(
        """<div id="root">
          <h1>  Title   here </h1>
          <p>First
             para<br>next   line</p>
          <p>Second <b>bold</b> <i>italic</i></p>
          <ul><li>one</li><li>two</li></ul>
          <table><tr><th>A</th><th>B</th></tr><tr><td> 1 </td><td>2</td></tr></table>
          <pre>
  keep   spaces
end</pre>
          <script>skipped()</script><style>.x{}</style>
          <div hidden>hidden</div><div style="display: none">gone</div>
          inline <span>tail</span>
        </div>""",
        url=URL,
    )
    root = await first(page, "#root")
    assert (await root.inner_text()).ok == (
        "Title here\n\n"
        "First para\nnext line\n\n"
        "Second bold italic\n\n"
        "one\ntwo\n"
        "A\tB\n1\t2\n"
        "  keep   spaces\nend\n"
        "inline tail"
    )
    cell = await first(page, "td")
    assert (await cell.inner_text()).ok == "1"
    assert (await GetInnerText("p", _).run(page)).ok == "First para\nnext line"


async def test_pre_drops_the_newline_after_its_start_tag() -> None:
    page = StaticPage.from_html("<pre>\nline</pre>", url=URL)
    assert (await GetText("pre", _).run(page)).ok == "line"


# --------------------------------------------------------------------------
# Selector forms
# --------------------------------------------------------------------------


async def test_css_query_and_query_all(page: StaticPage) -> None:
    articles = (await page.query_selector_all("section > article.product")).ok
    assert len(articles) == 2
    assert (await page.query_selector(".missing")).ok is None
    assert (await page.query_selector_all(".missing")).ok == []
    assert (await page.query_selector("css=.price")).ok is not None
    has = (await page.query_selector_all("article:has(.badge)")).ok
    assert [(await item.attribute("data-sku")).ok for item in has] == ["a1"]


async def test_css_selector_lists_return_document_order(page: StaticPage) -> None:
    found = (await page.query_selector_all(".badge, h3 a, .price")).ok
    texts = [(await item.text()).ok for item in found]
    assert texts == ["Alpha & Co", "10.00", "new", "Beta", "20.00"]


async def test_css_on_an_element_matches_descendants_with_document_context(
    page: StaticPage,
) -> None:
    article = await first(page, "article")
    # querySelectorAll semantics: ancestors outside the scope may match.
    in_section = (await article.query_selector_all("section .price")).ok
    assert len(in_section) == 1
    # The scope itself is never a result.
    assert (await article.query_selector("article")).ok is None
    assert (await article.query_selector_all(".price")).ok[0] is not None
    scoped = (await (await first(page, "section")).query_selector_all(":scope > *")).ok
    assert len(scoped) == 2
    assert (await article.query_selector(":scope")).ok is not None


async def test_implicit_tbody_matches_browsers(page: StaticPage) -> None:
    rows = (await page.query_selector_all("table > tbody > tr")).ok
    assert len(rows) == 3


async def test_xpath_selectors(page: StaticPage) -> None:
    on_page = (await page.query_selector_all("xpath=//article/h3/a")).ok
    assert len(on_page) == 2
    assert (await page.query_selector_all("xpath=html/body/section")).ok
    article = (await page.query_selector_all("article")).ok[1]
    # Like Playwright, "//" on an element is relative to it.
    relative = (await article.query_selector_all("xpath=//a")).ok
    assert [(await item.text()).ok for item in relative] == ["Beta"]
    child = (await article.query_selector("xpath=./p")).ok
    assert child is not None and (await child.text()).ok == "20.00"
    parent = (await article.query_selector("xpath=..")).ok
    assert parent is not None and (await parent.attribute("id")).ok == "catalog"
    absolute = (await article.query_selector_all("xpath=(//a)[1]")).ok
    assert [(await item.text()).ok for item in absolute] == ["Alpha & Co"]
    bare = (await page.query_selector_all("//p")).ok
    assert len(bare) == 2
    not_nodes = (await page.query_selector_all("xpath=count(//p)")).ok
    assert not_nodes == []


async def test_silk_selector_types_compile_for_the_static_backend(
    page: StaticPage,
) -> None:
    assert (await GetText(css(".badge"), _).run(page)).ok == "new"
    assert (await GetText(xpath("//p[@class='price']"), _).run(page)).ok == "10.00"
    by_id = Selector(SelectorType.ID, "stock")
    assert (await ElementExists(by_id, _).run(page)).ok is True
    by_class = Selector(SelectorType.CLASS, "featured")
    assert (await GetAttribute(by_class, _, attribute="data-sku").run(page)).ok == (
        "a1"
    )
    by_name = Selector(SelectorType.NAME, "qty")
    assert (await GetAttribute(by_name, _, attribute="value").run(page)).ok == "1"
    by_tag = Selector(SelectorType.TAG, "h3")
    assert len((await QueryAll(by_tag, _).run(page)).ok) == 2


async def test_self_selector_reads_the_scope_element(page: StaticPage) -> None:
    articles = (await QueryAll("article", _).run(page)).ok
    skus = [
        (await GetAttribute(SELF, _, attribute="data-sku").run(item)).ok
        for item in articles
    ]
    assert skus == ["a1", "b2"]
    on_page = await GetText(SELF, _).run(page)
    assert on_page.is_error() and isinstance(on_page.error, TypeError)


async def test_selector_group_falls_back_in_order(page: StaticPage) -> None:
    group = SelectorGroup(
        "price",
        css(".sale-price"),
        xpath("//p[contains(@class, 'price')]"),
        css(".price"),
    )
    assert (await GetText(group, _).run(page)).ok == "10.00"
    all_prices = (await QueryAll(group, _).run(page)).ok
    assert len(all_prices) == 2
    missing = await GetText(SelectorGroup("x", css(".a"), css(".b")), _).run(page)
    assert missing.is_error()
    assert isinstance(missing.error, ElementNotFoundError)
    assert missing.error.selector == (".a", ".b")


async def test_playwright_only_engines_are_unsupported(page: StaticPage) -> None:
    for selector in (
        "text=Alpha",
        'a:text-is("Alpha")',
        "article:has-text('Beta')",
        "section >> article",
        "role=button",
        '"Alpha"',
    ):
        result = await page.query_selector(selector)
        assert result.is_error(), selector
        assert isinstance(result.error, UnsupportedOperationError), selector
    via_text = await Query(text("Alpha"), _).run(page)
    assert isinstance(via_text.error, UnsupportedOperationError)
    link_text = await Query(Selector(SelectorType.LINK_TEXT, "Beta"), _).run(page)
    assert isinstance(link_text.error, UnsupportedOperationError)
    # Quoted values are not mistaken for engines.
    quoted = await page.query_selector('[title="text=Alpha >> :text-is(x)"]')
    assert quoted.is_ok() and quoted.ok is None


async def test_visible_pseudo_class_is_ignored(page: StaticPage) -> None:
    assert len((await page.query_selector_all("article:visible")).ok) == 2
    assert len((await page.query_selector_all("section > :visible")).ok) == 2
    assert (await page.query_selector(":visible")).ok is not None


async def test_invalid_selectors_are_browser_errors(page: StaticPage) -> None:
    css_error = await page.query_selector("div[[[")
    assert css_error.is_error() and isinstance(css_error.error, BrowserError)
    xpath_error = await page.query_selector("xpath=//p[")
    assert xpath_error.is_error() and isinstance(xpath_error.error, BrowserError)


# --------------------------------------------------------------------------
# Silk pipelines
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Product:
    title: str
    price: str
    url: str
    badge: str | None


extract_product = build(
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText(".price", _),
        "url": GetUrl("h3 > a", _),
        "badge": optional(GetText(".badge", _)),
    },
    Product,
)


async def test_extraction_pipeline_runs_on_a_static_page(page: StaticPage) -> None:
    products = await (QueryAll("article", _) >> traverse(extract_product)).run(page)
    assert products.ok == [
        Product("Alpha", "10.00", "https://example.com/shop/items/a1.html", "new"),
        Product("Beta", "20.00", "https://example.com/b2", None),
    ]


async def test_optional_does_not_hide_unsupported_selectors(page: StaticPage) -> None:
    result = await optional(GetText("text=Alpha", _)).run(page)
    assert result.is_error()


async def test_build_reports_missing_fields(page: StaticPage) -> None:
    broken = build({"x": GetText(".missing", _)})
    result = await broken.run(page)
    assert result.is_error() and isinstance(result.error, BuildFieldError)


async def test_extract_table(page: StaticPage) -> None:
    table = await ExtractTable("#stock", _).run(page)
    assert table.ok == [{"Name": "Alpha", "Qty": "1"}, {"Name": "Beta", "Qty": "2"}]
    headless = await ExtractTable("#stock", _, include_headers=False).run(page)
    assert headless.ok == [
        {"column_0": "Alpha", "column_1": "1"},
        {"column_0": "Beta", "column_1": "2"},
    ]


async def test_element_exists(page: StaticPage) -> None:
    assert (await ElementExists(".badge", _).run(page)).ok is True
    assert (await ElementExists(".nope", _).run(page)).ok is False


async def test_wait_for_element_with_groups(page: StaticPage) -> None:
    css_group = SelectorGroup("g", css(".missing"), css(".badge"))
    found = await WaitForElement(css_group, _).run(page)
    assert found.is_ok() and found.ok is not None
    assert (await found.ok.text()).ok == "new"

    mixed = SelectorGroup("m", xpath("//nope"), css(".price"))
    found = await WaitForElement(mixed, _).run(page)
    assert found.is_ok() and found.ok is not None

    neither = SelectorGroup("n", xpath("//nope"), css(".nope"))
    timed_out = await WaitForElement(neither, _).run(page)
    assert isinstance(timed_out.error, BrowserTimeoutError)

    gone = await WaitForElement(neither, _, options=WaitOptions(state="detached")).run(
        page
    )
    assert gone.is_ok() and gone.ok is None
    still_here = await WaitForElement(
        mixed, _, options=WaitOptions(state="hidden")
    ).run(page)
    assert isinstance(still_here.error, BrowserTimeoutError)


# --------------------------------------------------------------------------
# ParseHtml and Snapshot
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FakeResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes = field(repr=False)


async def test_parse_html_from_a_string() -> None:
    parsed = await ParseHtml(_).run("<title>T</title><p>x</p>")
    assert parsed.is_ok()
    assert (await parsed.ok.url()).ok == "about:blank"
    assert (await parsed.ok.title()).ok == "T"


async def test_parse_html_from_an_html_document() -> None:
    parsed = await ParseHtml(_).run(HtmlDocument(DOCUMENT, url=URL))
    assert parsed.is_ok()
    assert (await parsed.ok.url()).ok == URL
    products = await (QueryAll("article", _) >> traverse(extract_product)).run(
        parsed.ok
    )
    assert len(products.ok) == 2


async def test_parse_html_from_an_http_response() -> None:
    response = FakeResponse(
        url="https://example.com/r/",
        status=200,
        headers={"Content-Type": "text/html; charset=ISO-8859-1"},
        body="<a href='x'>caf\u00e9</a>".encode("latin-1"),
    )
    parsed = await (ParseHtml(_) >> GetText("a", _)).run(response)
    assert parsed.ok == "caf\u00e9"
    url = await (ParseHtml(_) >> GetUrl("a", _)).run(response)
    assert url.ok == "https://example.com/r/x"


def test_decode_body_rules() -> None:
    utf8 = "caf\u00e9".encode()
    assert decode_body(utf8, {}) == "caf\u00e9"
    assert decode_body(b"\xef\xbb\xbf" + utf8, {"content-type": "text/html"}) == (
        "caf\u00e9"
    )
    assert decode_body(b"caf\xe9", {}) == "caf\ufffd"
    assert decode_body(
        b"caf\xe9", {"CONTENT-TYPE": 'text/html; charset="latin-1"'}
    ) == ("caf\u00e9")
    assert decode_body(b"caf\xe9", {"content-type": "text/html; charset=bogus"}) == (
        "caf\ufffd"
    )
    meta = b'<meta charset="windows-1252"><p>caf\xe9</p>'
    assert "caf\u00e9" in decode_body(meta, {})


async def test_snapshots_of_static_values_are_identity(page: StaticPage) -> None:
    assert (await SnapshotPage(_).run(page)).ok is page
    article = await first(page, "article")
    assert (await SnapshotElement(_).run(article)).ok is article


def live_double(html: str) -> tuple[MagicMock, MagicMock]:
    """A stand-in live page and element answering like a browser would."""

    live_page = MagicMock(spec=Page)
    live_page.content = AsyncMock(return_value=Ok(html))
    live_page.url = AsyncMock(return_value=Ok("https://live.example/list"))
    live_page.base_url = AsyncMock(return_value=Ok("https://live.example/base/"))
    live_element = MagicMock(spec=ElementHandle)
    live_element.page = live_page
    return live_page, live_element


async def test_snapshot_page_copies_content_url_and_base_url() -> None:
    live_page, _element = live_double('<a href="x">x</a>')
    snapshot = await SnapshotPage(_).run(live_page)
    assert snapshot.is_ok()
    assert (await snapshot.ok.url()).ok == "https://live.example/list"
    assert (await snapshot.ok.base_url()).ok == "https://live.example/base/"
    assert (await GetUrl("a", _).run(snapshot.ok)).ok == ("https://live.example/base/x")
    live_page.content.assert_awaited_once()


async def test_snapshot_page_propagates_live_errors() -> None:
    live_page, _element = live_double("")
    live_page.content = AsyncMock(return_value=Error(BrowserError("closed")))
    snapshot = await SnapshotPage(_).run(live_page)
    assert snapshot.is_error() and isinstance(snapshot.error, BrowserError)


@pytest.mark.parametrize(
    ("outer", "tag", "inner_text"),
    [
        ('<article data-sku="a1"><a href="i/1">One</a></article>', "article", "One"),
        ("<tr><td>a</td><td>b</td></tr>", "tr", "a\tb"),
        ("<td>cell</td>", "td", "cell"),
        ("<li>item</li>", "li", "item"),
    ],
)
async def test_snapshot_element_roots_a_small_page(
    outer: str, tag: str, inner_text: str
) -> None:
    _page, live_element = live_double("")
    live_element.html = AsyncMock(return_value=Ok(outer))
    snapshot = await SnapshotElement(_).run(live_element)
    assert snapshot.is_ok(), snapshot
    element = snapshot.ok
    assert element.tag == tag
    assert element.selector is None
    assert (await element.inner_text()).ok == inner_text
    assert (await element.page.url()).ok == "https://live.example/list"
    live_element.html.assert_awaited_once_with(outer=True)


async def test_snapshot_element_reads_fields_in_process() -> None:
    _page, live_element = live_double("")
    live_element.html = AsyncMock(
        return_value=Ok(
            '<article><h3><a href="i/1" title="T">x</a></h3>'
            '<p class="price">1</p></article>'
        )
    )
    product = await (SnapshotElement(_) >> extract_product).run(live_element)
    assert product.ok == Product("T", "1", "https://live.example/base/i/1", None)
    assert (
        await GetAttribute(SELF, _, attribute="class").run(
            (await SnapshotElement(_).run(live_element)).ok
        )
    ).ok is None
