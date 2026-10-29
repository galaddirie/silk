# pyright: strict
"""Static-HTML backend: Silk's ``Page``/``ElementHandle`` over parsed HTML.

The same extraction pipelines (``Query``, ``QueryAll``, ``GetText``,
``GetAttribute``, ``GetUrl``, ``ExtractTable``, ``ElementExists``,
``WaitForElement``, ``optional(...)``, ``SELF`` ...) run unchanged on:

* HTML obtained without a browser: :func:`ParseHtml` / :meth:`StaticPage.from_html`;
* a one-round-trip snapshot of a live page or element: :func:`SnapshotPage` and
  :func:`SnapshotElement`, which turn every later field read into an in-process
  lookup instead of one browser call each::

      books = (
          Navigate(_, "https://books.toscrape.com/")
          >> SnapshotPage(_)
          >> QueryAll("article.product_pod", _)
          >> traverse(extract_book)
      )

HTML is parsed with ``lxml.html`` (libxml2). CSS selectors are translated to
XPath with ``cssselect``; XPath selectors run on lxml directly. Requires the
``silk-scraper[static]`` extra (``lxml`` and ``cssselect``).

Selector support mirrors what Silk compiles and Playwright accepts:

* plain CSS, including selector lists (``"a, b"``), attribute forms
  (``[id="x"]``, ``[class~="x"]``, ``[name="x"]``) and ``:scope``; an optional
  ``css=`` prefix is accepted;
* ``xpath=...`` (and, like Playwright, bare selectors starting with ``//`` or
  ``..``). On an element, an expression starting with ``/`` is relative to it;
* Playwright's ``:visible`` is ignored: static HTML has no layout, so every
  element counts as visible.

Playwright-only engines (``text=``, ``a:text-is(...)``, ``:has-text(...)``,
``>>`` chains, ...) return ``Error(UnsupportedOperationError(...))``.

CSS on an element follows ``querySelectorAll`` semantics: the whole selector
is matched against the document and the results are filtered to the element's
descendants, so ``"section a"`` on a ``div`` inside a ``section`` matches.

Parsing differs from a browser's HTML5 parser in corner cases. Two common
differences are normalised: ``<tr>`` rows written directly inside ``<table>``
are wrapped in an implicit ``<tbody>``, and the newline right after ``<pre>``,
``<listing>`` or ``<textarea>`` is dropped.
"""

from __future__ import annotations

import codecs
import re
from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Never, Protocol, TypeAlias, TypeGuard, cast, overload
from urllib.parse import urljoin
from uuid import uuid4

import lxml.html
from cssselect import HTMLTranslator, SelectorError
from fp_ops import Error, Ok, Result, result_operation_template
from lxml import etree

from silk.browsers.models import (
    CoordinateType,
    ElementHandle,
    Frame,
    KeyModifier,
    MouseButtonLiteral,
    NavigationWaitLiteral,
    Page,
    WaitStateLiteral,
)
from silk.errors import BrowserError, BrowserTimeoutError, UnsupportedOperationError

_Node: TypeAlias = etree._Element  # pyright: ignore[reportPrivateUsage]

STATIC_CONTEXT_ID = "static"
"""The ``context_id`` of every static page and element."""

_NO_EVALUATION_ARGUMENT = object()
_EMPTY_DOCUMENT = "<html><head></head><body></body></html>"
_TRANSLATOR = HTMLTranslator()

# --------------------------------------------------------------------------
# Selector compilation
# --------------------------------------------------------------------------

_PLAYWRIGHT_ENGINES = frozenset(
    {
        "text",
        "id",
        "data-testid",
        "data-test-id",
        "data-test",
        "role",
        "nth",
        "visible",
        "internal",
        "_react",
        "_vue",
    }
)
_ENGINE_PREFIX = re.compile(r"^\s*([A-Za-z_][\w-]*)(?::[\w-]+)*\s*=")
_PLAYWRIGHT_PSEUDO = re.compile(
    r":(text|text-is|text-matches|has-text|nth-match|light|near|left-of|"
    r"right-of|above|below)(?![\w-])"
)
_VISIBLE_PSEUDO = re.compile(r":visible(?![\w(-])")
_SCOPE_PSEUDO = re.compile(r":scope(?![\w-])")
_FUNCTION_START = re.compile(r"^([A-Za-z_][\w.-]*)\s*\(")
_NODE_TESTS = frozenset({"node", "text", "comment", "processing-instruction"})


def _mask_quotes(selector: str) -> str:
    """Blank out quoted strings so syntax searches ignore attribute values."""

    masked: list[str] = []
    quote: str | None = None
    escaped = False
    for char in selector:
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
                masked.append(char)
                continue
            masked.append("_")
            continue
        if char in "\"'":
            quote = char
        masked.append(char)
    return "".join(masked)


def _unsupported_selector(selector: str, reason: str) -> UnsupportedOperationError:
    return UnsupportedOperationError(
        f"selector {selector!r} is not supported by the static backend: {reason}"
    )


def _strip_visible(css: str) -> str:
    masked = _mask_quotes(css)
    for match in reversed(list(_VISIBLE_PSEUDO.finditer(masked))):
        start, end = match.span()
        before = masked[start - 1] if start > 0 else ""
        compound = before != "" and (before.isalnum() or before in "-_*])\\")
        css = css[:start] + ("" if compound else "*") + css[end:]
    return css


@dataclass(frozen=True, slots=True)
class _CssQuery:
    xpath: str
    scoped: bool
    scope_only: bool


@dataclass(frozen=True, slots=True)
class _XPathQuery:
    expression: str


_Query: TypeAlias = _CssQuery | _XPathQuery


@lru_cache(maxsize=1024)
def _xpath(expression: str) -> etree.XPath:
    return etree.XPath(expression)


@lru_cache(maxsize=1024)
def _css_to_xpath(css: str) -> str:
    return _TRANSLATOR.css_to_xpath(css)


def _compile_css(selector: str, css: str) -> Result[_Query, Exception]:
    masked = _mask_quotes(css)
    if ">>" in masked:
        return Error(_unsupported_selector(selector, "'>>' chains are Playwright-only"))
    pseudo = _PLAYWRIGHT_PSEUDO.search(masked)
    if pseudo is not None:
        return Error(
            _unsupported_selector(
                selector, f"':{pseudo.group(1)}' is a Playwright text/layout engine"
            )
        )
    css = _strip_visible(css).strip()
    if css == ":scope":
        return Ok(_CssQuery(xpath="", scoped=True, scope_only=True))
    try:
        translated = _css_to_xpath(css)
        _xpath(translated)
    except (SelectorError, etree.XPathSyntaxError) as error:
        failure = BrowserError(f"invalid CSS selector {selector!r}: {error}")
        failure.__cause__ = error
        return Error(failure)
    scoped = _SCOPE_PSEUDO.search(_mask_quotes(css)) is not None
    return Ok(_CssQuery(xpath=translated, scoped=scoped, scope_only=False))


def _compile(selector: str) -> Result[_Query, Exception]:
    stripped = selector.strip()
    if stripped.startswith("xpath="):
        return Ok(_XPathQuery(stripped.removeprefix("xpath=").strip()))
    if stripped.startswith("css="):
        return _compile_css(selector, stripped.removeprefix("css="))
    if stripped.startswith(("//", "..")):
        return Ok(_XPathQuery(stripped))
    if stripped.startswith(("'", '"')):
        return Error(_unsupported_selector(selector, "quoted text is Playwright-only"))
    engine = _ENGINE_PREFIX.match(stripped)
    if engine is not None and (
        engine.group(1) in _PLAYWRIGHT_ENGINES or engine.group(1).startswith("internal")
    ):
        return Error(
            _unsupported_selector(
                selector, f"the {engine.group(1)!r} engine is Playwright-only"
            )
        )
    return _compile_css(selector, stripped)


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------


def _is_element(node: object) -> TypeGuard[_Node]:
    return isinstance(node, _Node) and isinstance(node.tag, str)


def _child_elements(node: _Node) -> list[_Node]:
    return [child for child in node if isinstance(child.tag, str)]


def _elements_only(found: object) -> list[_Node]:
    """The element nodes of an XPath result, in order and without repeats."""

    if not isinstance(found, list):
        return []
    elements: list[_Node] = []
    seen: set[int] = set()
    for item in cast(list[object], found):
        if _is_element(item) and id(item) not in seen:
            seen.add(id(item))
            elements.append(item)
    return elements


def _wrap_table_rows(root: _Node) -> None:
    """Insert the ``<tbody>`` a browser's parser adds around bare table rows."""

    for table in list(root.iter("table")):
        children = list(table)
        index = 0
        while index < len(children):
            if children[index].tag != "tr":
                index += 1
                continue
            run_end = index
            while run_end < len(children) and children[run_end].tag == "tr":
                run_end += 1
            body = table.makeelement("tbody")
            table.insert(table.index(children[index]), body)
            for row in children[index:run_end]:
                body.append(row)
            index = run_end


def _drop_leading_newline(root: _Node) -> None:
    for element in root.iter("pre", "listing", "textarea"):
        text = element.text
        if text is not None and text.startswith("\r\n"):
            element.text = text[2:]
        elif text is not None and text.startswith("\n"):
            element.text = text[1:]


_XML_DECLARATION = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)
_DOCTYPE = re.compile(r"^\s*(?:<!--.*?-->\s*)*<!doctype", re.IGNORECASE | re.DOTALL)


_TRAILING_SPACE = re.compile(
    r"</body\s*>(\s*)(?:</html\s*>(\s*))?\Z|</html\s*>(\s*)\Z", re.IGNORECASE
)


def _keep_trailing_space(root: _Node, html: str) -> None:
    """Move whitespace after ``</body>`` into the body, as browsers do."""

    found = _TRAILING_SPACE.search(html)
    body = root.find("body")
    if found is None or body is None:
        return
    space = "".join(group or "" for group in found.groups())
    if not space:
        return
    children = list(body)
    if children:
        children[-1].tail = (children[-1].tail or "") + space
    else:
        body.text = (body.text or "") + space


def _parse(html: str) -> _Node:
    html = _XML_DECLARATION.sub("", html, count=1)
    if not html.strip():
        html = _EMPTY_DOCUMENT
    try:
        root = lxml.html.document_fromstring(html, ensure_head_body=True)
    except etree.ParserError:
        root = lxml.html.document_fromstring(_EMPTY_DOCUMENT)
    _wrap_table_rows(root)
    _drop_leading_newline(root)
    _keep_trailing_space(root, html)
    return root


class _Document:
    """A parsed, never-mutated document plus lazily built lookup indexes."""

    def __init__(self, root: _Node, *, doctype: str | None) -> None:
        self.root = root
        self.doctype = doctype
        self._order: dict[_Node, int] | None = None
        self._ends: dict[_Node, int] = {}
        self._matches: dict[str, tuple[list[_Node], list[int]]] = {}

    def _index(self) -> dict[_Node, int]:
        if self._order is None:
            order: dict[_Node, int] = {}
            counter = 0
            stack: list[tuple[_Node, bool]] = [(self.root, False)]
            while stack:
                node, finished = stack.pop()
                if finished:
                    self._ends[node] = counter - 1
                    continue
                order[node] = counter
                counter += 1
                stack.append((node, True))
                stack.extend(
                    (child, False) for child in reversed(_child_elements(node))
                )
            self._order = order
        return self._order

    def _all_matches(self, xpath: str) -> tuple[list[_Node], list[int]]:
        cached = self._matches.get(xpath)
        if cached is None:
            order = self._index()
            nodes = _elements_only(_xpath(xpath)(self.root))
            cached = self._matches[xpath] = (nodes, [order[node] for node in nodes])
        return cached

    def css(self, query: _CssQuery, scope: _Node | None) -> list[_Node]:
        if query.scope_only:
            return [self.root if scope is None else scope]
        if query.scoped:
            context = self.root if scope is None else scope
            found = _elements_only(_xpath(query.xpath)(context))
            if scope is None:
                return found
            return [
                node for node in found if node is not scope and _contains(scope, node)
            ]
        nodes, positions = self._all_matches(query.xpath)
        if scope is None:
            return list(nodes)
        order = self._index()
        start = bisect_right(positions, order[scope])
        stop = bisect_right(positions, self._ends[scope])
        return nodes[start:stop]

    def xpath(self, expression: str, scope: _Node | None) -> list[_Node]:
        if scope is None:
            function = _FUNCTION_START.match(expression)
            if not expression.startswith(("/", "(")) and (
                function is None or function.group(1) in _NODE_TESTS
            ):
                expression = "/" + expression
            return _elements_only(_xpath(expression)(self.root.getroottree()))
        if expression.startswith("/"):
            expression = "." + expression
        return _elements_only(_xpath(expression)(scope))

    def query(
        self, selector: str, scope: _Node | None
    ) -> Result[list[_Node], Exception]:
        compiled = _compile(selector)
        if compiled.is_error():
            return Error(compiled.error)
        query = compiled.ok
        try:
            if isinstance(query, _CssQuery):
                return Ok(self.css(query, scope))
            return Ok(self.xpath(query.expression, scope))
        except etree.XPathError as error:
            failure = BrowserError(f"invalid selector {selector!r}: {error}")
            failure.__cause__ = error
            return Error(failure)


def _text_content(node: _Node) -> str:
    return str(_xpath("string()")(node))


def _contains(ancestor: _Node, node: _Node) -> bool:
    return any(parent is ancestor for parent in node.iterancestors())


# --------------------------------------------------------------------------
# Text and HTML reads
# --------------------------------------------------------------------------

_RAW_TEXT = frozenset({"script", "style", "xmp", "iframe", "noembed", "noframes"})
_NOT_RENDERED = frozenset(
    {
        "head",
        "script",
        "style",
        "template",
        "noscript",
        "title",
        "meta",
        "link",
        "base",
        "iframe",
        "datalist",
    }
)
_BLOCKS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "body",
        "caption",
        "center",
        "dd",
        "details",
        "dialog",
        "dir",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hgroup",
        "hr",
        "html",
        "legend",
        "li",
        "listing",
        "main",
        "menu",
        "nav",
        "ol",
        "pre",
        "section",
        "summary",
        "table",
        "tr",
        "ul",
    }
)
_PRESERVE_WHITESPACE = frozenset({"pre", "listing", "textarea", "plaintext"})
_CELLS = frozenset({"td", "th"})
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none", re.IGNORECASE)
_COLLAPSIBLE = re.compile(r"[ \t\n\r\f]+")
# Private-use stand-ins keep preserved whitespace out of the collapsing passes.
_KEEP = str.maketrans({" ": "\ue000", "\n": "\ue001", "\t": "\ue002"})
_RESTORE = str.maketrans({"\ue000": " ", "\ue001": "\n", "\ue002": "\t"})


def _hidden(node: _Node) -> bool:
    style = node.get("style")
    return (
        node.tag in _NOT_RENDERED
        or node.get("hidden") is not None
        or (style is not None and _HIDDEN_STYLE.search(style) is not None)
    )


def _inner_text(node: _Node) -> str:
    """Approximate ``HTMLElement.innerText`` without a layout engine.

    Implements the spec's algorithm with tag-based display values: blocks
    produce line breaks (two around ``<p>``), ``<br>`` a newline, table cells
    a tab, whitespace collapses outside ``<pre>``-like elements. Non-rendered
    elements (``<script>``, ``hidden``, inline ``display: none``) are skipped;
    stylesheets, ``visibility``, ``text-transform`` and generated content are
    not considered.
    """

    if node.tag in _RAW_TEXT or node.tag in {"textarea", "title"}:
        return _text_content(node)
    items: list[str | int] = []

    def text(value: str | None, preserve: bool) -> None:
        if value:
            items.append(
                value.translate(_KEEP) if preserve else _COLLAPSIBLE.sub(" ", value)
            )

    def walk(element: _Node, preserve: bool) -> None:
        tag = element.tag
        if tag == "br":
            items.append("\n")
            return
        block = tag in _BLOCKS or tag == "p"
        breaks = 2 if tag == "p" else 1
        if block:
            items.append(breaks)
        preserve = preserve or tag in _PRESERVE_WHITESPACE
        text(element.text, preserve)
        for child in element:
            if isinstance(child.tag, str) and not _hidden(child):
                walk(child, preserve)
            text(child.tail, preserve)
        if tag in _CELLS and element is not node:
            following = element.getnext()
            while following is not None and not isinstance(following.tag, str):
                following = following.getnext()
            if following is not None and following.tag in _CELLS:
                items.append("\t")
        if block:
            items.append(breaks)

    walk(node, False)
    output: list[str] = []
    pending = 0
    run: list[str] = []
    for item in [*items, 0]:
        if isinstance(item, str):
            run.append(item)
            continue
        line = re.sub(r" +", " ", "".join(run))
        line = re.sub(r" *([\n\t]) *", r"\1", line).strip(" ")
        run.clear()
        if line:
            if pending and output:
                output.append("\n" * pending)
            output.append(line)
            pending = 0
        pending = max(pending, item)
    return "".join(output).translate(_RESTORE)


def _outer_html(node: _Node) -> str:
    return etree.tostring(node, method="html", encoding="unicode", with_tail=False)


def _inner_html(node: _Node) -> str:
    raw = node.tag in _RAW_TEXT
    parts = [node.text or "" if raw else escape(node.text or "", quote=False)]
    parts.extend(
        etree.tostring(child, method="html", encoding="unicode", with_tail=True)
        for child in node
    )
    return "".join(parts)


def _title(root: _Node) -> str:
    for title in root.iter("title"):
        return " ".join(_text_content(title).split())
    return ""


def _base_href(root: _Node) -> str | None:
    for base in root.iter("base"):
        href = base.get("href")
        if href is not None:
            return href.strip()
    return None


def _unsupported(operation: str) -> Result[Never, Exception]:
    return Error(
        UnsupportedOperationError(
            f"{operation} is not supported on static HTML (there is no browser)"
        )
    )


# --------------------------------------------------------------------------
# Page and element
# --------------------------------------------------------------------------


def _select(
    page: StaticPage,
    document: _Document,
    selector: str,
    scope: _Node | None,
) -> Result[list[StaticElement], Exception]:
    found = document.query(selector, scope)
    return found.map(
        lambda nodes: [StaticElement(node, page, document, selector) for node in nodes]
    )


class StaticElement(ElementHandle):
    """An element of a :class:`StaticPage`. Reads only; interactions fail.

    Interactions (click, fill, type, ...) return
    ``Error(UnsupportedOperationError)``; :meth:`content_frame` is always
    ``None`` because iframes are not loaded.
    """

    def __init__(
        self,
        node: _Node,
        page: StaticPage,
        document: _Document,
        selector: str | None,
    ) -> None:
        self._node = node
        self._page = page
        self._document = document
        self._selector = selector

    @property
    def page(self) -> StaticPage:
        return self._page

    @property
    def page_id(self) -> str:
        return self._page.page_id

    @property
    def context_id(self) -> str:
        return self._page.context_id

    @property
    def selector(self) -> str | None:
        return self._selector

    @property
    def tag(self) -> str:
        """The element's lower-case tag name."""

        return str(self._node.tag)

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        return _select(self._page, self._document, selector, self._node).map(
            lambda found: found[0] if found else None
        )

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        return _select(self._page, self._document, selector, self._node).map(
            lambda found: list[ElementHandle](found)
        )

    async def click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        click_count: int = 1,
        force: bool = False,
        position: tuple[float, float] | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("click")

    async def content_frame(self) -> Result[Frame | None, Exception]:
        return Ok(None)

    async def double_click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        force: bool = False,
    ) -> Result[None, Exception]:
        return _unsupported("double_click")

    async def fill(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear: bool = False,
    ) -> Result[None, Exception]:
        return _unsupported("fill")

    async def type(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("type")

    async def select(
        self,
        *,
        value: str | None = None,
        text: str | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("select")

    async def scroll_into_view(self) -> Result[None, Exception]:
        return _unsupported("scroll_into_view")

    async def text(self) -> Result[str, Exception]:
        """``textContent``: all descendant text, including ``<script>`` text."""

        return Ok(_text_content(self._node))

    async def inner_text(self) -> Result[str, Exception]:
        """An approximation of ``innerText`` (see :func:`_inner_text`)."""

        return Ok(_inner_text(self._node))

    async def html(self, *, outer: bool = True) -> Result[str, Exception]:
        return Ok(_outer_html(self._node) if outer else _inner_html(self._node))

    async def attribute(self, name: str) -> Result[str | None, Exception]:
        return Ok(self._node.get(name.lower()))

    async def move_pointer_to(
        self,
        *,
        offset: CoordinateType = (0, 0),
        center: bool = True,
        steps: int = 1,
    ) -> Result[None, Exception]:
        return _unsupported("move_pointer_to")

    async def drag_to(
        self,
        target: ElementHandle,
        *,
        steps: int = 1,
        move_to_center: bool = True,
        position_offset: CoordinateType | None = None,
        source_offset: CoordinateType | None = None,
        target_offset: CoordinateType | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("drag_to")


class StaticPage(Page):
    """An immutable page parsed from HTML; every read resolves in-process.

    ``wait_for_selector`` answers immediately from the parsed document.
    Navigation, ``evaluate``, ``screenshot``, mouse, keyboard and ``scroll``
    return ``Error(UnsupportedOperationError)``; ``close`` is a no-op.
    """

    def __init__(
        self,
        document: _Document,
        *,
        url: str,
        base_url: str,
    ) -> None:
        self._document = document
        self._url = url
        self._base_url = base_url
        self._page_id = str(uuid4())

    @classmethod
    def from_html(
        cls,
        html: str,
        *,
        url: str = "about:blank",
        base_url: str | None = None,
    ) -> StaticPage:
        """Parse ``html`` as the document at ``url``.

        ``base_url`` overrides the URL relative links resolve against;
        otherwise it is ``<base href>`` resolved against ``url``, or ``url``.
        """

        root = _parse(html)
        doctype = None
        if _DOCTYPE.match(html) is not None:
            doctype = root.getroottree().docinfo.doctype or None
        if base_url is None:
            href = _base_href(root)
            base_url = url if href is None else urljoin(url, href)
        return cls(_Document(root, doctype=doctype), url=url, base_url=base_url)

    @property
    def root(self) -> StaticElement:
        """The document element (``<html>``) as an element scope."""

        return StaticElement(self._document.root, self, self._document, None)

    @property
    def page_id(self) -> str:
        return self._page_id

    @property
    def context_id(self) -> str:
        return STATIC_CONTEXT_ID

    async def navigate(
        self,
        url: str,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
        referer: str | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("navigate")

    async def url(self) -> Result[str, Exception]:
        return Ok(self._url)

    async def base_url(self) -> Result[str, Exception]:
        return Ok(self._base_url)

    async def title(self) -> Result[str, Exception]:
        return Ok(_title(self._document.root))

    async def content(self) -> Result[str, Exception]:
        html = _outer_html(self._document.root)
        doctype = self._document.doctype
        return Ok(html if doctype is None else f"{doctype}\n{html}")

    async def reload(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        return _unsupported("reload")

    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        return _unsupported("go_back")

    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        return _unsupported("go_forward")

    async def wait_for_navigation(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        return _unsupported("wait_for_navigation")

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        return _select(self, self._document, selector, None).map(
            lambda found: found[0] if found else None
        )

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        return _select(self, self._document, selector, None).map(
            lambda found: list[ElementHandle](found)
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout_ms: int | None = None,
        state: WaitStateLiteral = "visible",
    ) -> Result[ElementHandle | None, Exception]:
        """Answer at once: a static document never changes.

        ``visible``/``attached`` return the element or time out immediately;
        ``hidden``/``detached`` return ``None`` when absent or time out.
        """

        found = _select(self, self._document, selector, None)
        if found.is_error():
            return Error(found.error)
        elements = found.ok
        if state in ("visible", "attached"):
            if elements:
                return Ok(elements[0])
            return Error(
                BrowserTimeoutError(
                    f"no element matches {selector!r} in the static document"
                )
            )
        if not elements:
            return Ok(None)
        return Error(
            BrowserTimeoutError(
                f"{selector!r} is present in the static document and cannot become {state}"
            )
        )

    @overload
    async def evaluate(self, script: str) -> Result[object, Exception]: ...

    @overload
    async def evaluate(
        self,
        script: str,
        argument: object,
    ) -> Result[object, Exception]: ...

    async def evaluate(
        self,
        script: str,
        argument: object = _NO_EVALUATION_ARGUMENT,
    ) -> Result[object, Exception]:
        return _unsupported("evaluate")

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]: ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]: ...

    async def screenshot(
        self,
        path: Path | None = None,
    ) -> Result[Path | bytes, Exception]:
        return _unsupported("screenshot")

    async def mouse_move(
        self,
        x: float,
        y: float,
        *,
        steps: int = 1,
    ) -> Result[None, Exception]:
        return _unsupported("mouse_move")

    async def mouse_down(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        return _unsupported("mouse_down")

    async def mouse_up(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        return _unsupported("mouse_up")

    async def key_press(
        self,
        key: str,
        *,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        return _unsupported("key_press")

    async def key_down(self, key: str) -> Result[None, Exception]:
        return _unsupported("key_down")

    async def key_up(self, key: str) -> Result[None, Exception]:
        return _unsupported("key_up")

    async def scroll(self, *, x: int = 0, y: int = 0) -> Result[None, Exception]:
        return _unsupported("scroll")

    async def close(self) -> Result[None, Exception]:
        return Ok(None)


# --------------------------------------------------------------------------
# Sources and templates
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HtmlDocument:
    """HTML text and the URL it was served from."""

    html: str
    url: str = "about:blank"


class HttpResponseLike(Protocol):
    """Any HTTP response with a final URL, headers and a raw body.

    Matched structurally, so an ``HttpResponse(url, status, headers, body)``
    from any HTTP client wrapper is accepted without importing it.
    """

    @property
    def url(self) -> str: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def body(self) -> bytes: ...


HtmlSource: TypeAlias = str | HtmlDocument | HttpResponseLike
"""What :func:`ParseHtml` accepts: bare HTML (URL ``about:blank``), an
:class:`HtmlDocument`, or an :class:`HttpResponseLike`."""

_CHARSET = re.compile(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9._:-]+)""", re.IGNORECASE)
_META_CHARSET = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._:-]+)""", re.IGNORECASE
)


def _known_encoding(name: bytes | str | None) -> str | None:
    if name is None:
        return None
    label = name.decode("ascii", "replace") if isinstance(name, bytes) else name
    try:
        return codecs.lookup(label).name
    except LookupError:
        return None


def _content_type_charset(headers: Mapping[str, str]) -> str | None:
    for key, value in headers.items():
        if key.lower() == "content-type":
            found = _CHARSET.search(value.encode("latin-1", "replace"))
            return _known_encoding(None if found is None else found.group(1))
    return None


def decode_body(body: bytes, headers: Mapping[str, str]) -> str:
    """Decode an HTML body: BOM, then ``Content-Type`` charset, then
    ``<meta charset>`` in the first 1024 bytes, else UTF-8. Undecodable bytes
    become U+FFFD."""

    if body.startswith(codecs.BOM_UTF8):
        return body.removeprefix(codecs.BOM_UTF8).decode("utf-8", "replace")
    encoding = _content_type_charset(headers)
    if encoding is None:
        meta = _META_CHARSET.search(body[:1024])
        encoding = _known_encoding(None if meta is None else meta.group(1))
    return body.decode(encoding or "utf-8", "replace")


@result_operation_template
def ParseHtml(source: HtmlSource) -> Result[StaticPage, Exception]:
    """Parse HTML into a :class:`StaticPage` that Silk's extraction actions query.

    ``source`` is one closed union rather than an "anything with ``.text``"
    protocol, so the type checker can check every caller and the decoding rule
    lives in one place:

    * ``str``: the HTML itself, at URL ``about:blank``;
    * :class:`HtmlDocument`: already decoded HTML and its URL;
    * :class:`HttpResponseLike`: ``url``, ``headers`` and raw ``body`` bytes,
      decoded with :func:`decode_body`.
    """

    if isinstance(source, str):
        html, url = source, "about:blank"
    elif isinstance(source, HtmlDocument):
        html, url = source.html, source.url
    else:
        html, url = decode_body(source.body, source.headers), source.url
    try:
        return Ok(StaticPage.from_html(html, url=url))
    except (etree.LxmlError, ValueError) as error:
        return Error(error)


@result_operation_template
async def SnapshotPage(page: Page) -> Result[StaticPage, Exception]:
    """Copy a live page into a :class:`StaticPage` in one ``content()`` call.

    The live URL and base URL are kept, so ``GetUrl`` resolves links the same
    way. A :class:`StaticPage` input is returned unchanged.
    """

    if isinstance(page, StaticPage):
        return Ok(page)
    content = await page.content()
    if content.is_error():
        return Error(content.error)
    url = await page.url()
    if url.is_error():
        return Error(url.error)
    base = await page.base_url()
    if base.is_error():
        return Error(base.error)
    return Ok(StaticPage.from_html(content.ok, url=url.ok, base_url=base.ok))


_START_TAG = re.compile(r"^\s*<([A-Za-z][^\s/>]*)")


@result_operation_template
async def SnapshotElement(element: ElementHandle) -> Result[StaticElement, Exception]:
    """Copy a live element (its ``outerHTML``) into a :class:`StaticElement`.

    The snapshot is the root of a small :class:`StaticPage` carrying the live
    page's URL and base URL. Its ancestors are not copied, so CSS selectors
    that rely on them (``"section a"`` from inside the ``section``) do not
    match. A :class:`StaticElement` input is returned unchanged.
    """

    if isinstance(element, StaticElement):
        return Ok(element)
    outer = await element.html(outer=True)
    if outer.is_error():
        return Error(outer.error)
    url = await element.page.url()
    if url.is_error():
        return Error(url.error)
    base = await element.page.base_url()
    if base.is_error():
        return Error(base.error)
    tag = _START_TAG.match(outer.ok)
    if tag is None:
        return Error(BrowserError("element HTML has no start tag"))
    document = _Document(_parse(outer.ok), doctype=None)
    snapshot = StaticPage(document, url=url.ok, base_url=base.ok)
    name = tag.group(1).lower()
    for node in document.root.iter(name):
        return Ok(StaticElement(node, snapshot, document, None))
    return Error(BrowserError(f"could not parse a <{name}> from the element HTML"))


__all__ = [
    "STATIC_CONTEXT_ID",
    "HtmlDocument",
    "HtmlSource",
    "HttpResponseLike",
    "ParseHtml",
    "SnapshotElement",
    "SnapshotPage",
    "StaticElement",
    "StaticPage",
    "decode_body",
]
