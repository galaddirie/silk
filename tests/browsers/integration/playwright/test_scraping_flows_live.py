"""Live Chromium contracts for 0.5 scraping features."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterator
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

import pytest
from fp_ops import (
    _,
    build,
    retry,
    traverse_all_settled,
    traverse_parallel,
)

from silk.actions.browser import CreateContext
from silk.actions.elements import (
    ContentFrame,
    GetAttribute,
    GetText,
    GetUrl,
    OwnerPage,
    QueryAll,
    WaitForElement,
    WaitOptions,
    optional,
)
from silk.actions.input import Click, ClickOptions
from silk.actions.navigation import Navigate
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserOptions,
    RequestBlocking,
)
from silk.browsers.sessions import BrowserSession
from silk.errors import (
    BrowserTimeoutError,
    ChangeTimeoutError,
    ElementNotFoundError,
    NavigationError,
)
from silk.scraping import await_change, in_new_page
from silk.selectors import SELF, SelectorGroup, css, xpath

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def html(body: str) -> str:
    return f"data:text/html,{quote(body)}"


class _Site(BaseHTTPRequestHandler):
    requested: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        _Site.requested.append(self.path)
        if self.path.startswith("/page"):
            body = (
                b"<base href='/docs/'><a id='rel' href='guide?x=1'>g</a>"
                b"<a id='abs' href='//cdn.test/a.js'>a</a>"
                b"<img src='/pixel.png'><script src='/blocked.js'></script>"
            )
            content_type = "text/html"
        else:
            body = b""
            content_type = (
                "image/png" if self.path.endswith(".png") else "text/javascript"
            )
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        return


@pytest.fixture
def site() -> Iterator[str]:
    _Site.requested = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


async def test_native_failures_become_silk_errors(
    browser_session: BrowserSession,
) -> None:
    page = browser_session.page
    refused = await Navigate(_, "http://127.0.0.1:9/").run(page)
    assert isinstance(refused.error, NavigationError)
    assert refused.error.url == "http://127.0.0.1:9/"
    assert refused.error.__cause__ is not None

    await Navigate(_, html("<p>x</p>")).run(page)
    waited = await WaitForElement("#never", _, options=WaitOptions(timeout=100)).run(
        page
    )
    assert isinstance(waited.error, BrowserTimeoutError)


async def test_request_blocking_and_url_resolution(site: str) -> None:
    blocking = RequestBlocking(
        resource_types=frozenset({"image"}), url_patterns=("*/blocked.js",)
    )
    async with BrowserSession(
        BrowserOptions(headless=True),
        context_options=BrowserContextOptions(blocking=blocking),
    ) as session:
        page = session.page
        assert (await Navigate(_, f"{site}/page").run(page)).is_ok()
        await asyncio.sleep(0.2)
        assert "/page" in _Site.requested
        assert "/pixel.png" not in _Site.requested
        assert "/blocked.js" not in _Site.requested

        relative = await GetUrl("#rel", _).run(page)
        assert relative.ok == f"{site}/docs/guide?x=1"
        protocol_relative = await GetUrl("#abs", _).run(page)
        assert protocol_relative.ok == "http://cdn.test/a.js"
        missing = await GetUrl("#nope", _).run(page)
        assert isinstance(missing.error, ElementNotFoundError)


async def test_self_optional_and_owner_page(browser_session: BrowserSession) -> None:
    page = browser_session.page
    await Navigate(
        _, html("<ul><li id='a' data-n='1'>one</li><li id='b'>two</li></ul>")
    ).run(page)

    card = build(
        {
            "id": GetAttribute(SELF, _, attribute="id"),
            "text": GetText(SELF, _),
            "n": GetAttribute(SELF, _, attribute="data-n"),
            "missing": optional(GetText(".nothing", _)),
        }
    )
    cards = await (QueryAll("li", _) >> traverse_all_settled(card, limit=2)).run(page)
    assert [result.ok for result in cards.ok] == [
        {"id": "a", "text": "one", "n": "1", "missing": None},
        {"id": "b", "text": "two", "n": None, "missing": None},
    ]

    on_page = await GetText(SELF, _).run(page)
    assert isinstance(on_page.error, TypeError)

    owner = await (QueryAll("li", _).map(lambda items: items[0]) >> OwnerPage(_)).run(
        page
    )
    assert owner.ok is page


async def test_group_waits_race_css_and_xpath(browser_session: BrowserSession) -> None:
    page = browser_session.page
    await Navigate(
        _,
        html(
            "<main></main><script>setTimeout(() => {"
            "document.querySelector('main').innerHTML = '<p class=late>ok</p>'}, 150)</script>"
        ),
    ).run(page)
    group = SelectorGroup("late", css(".never"), xpath("//p[@class='late']"))
    found = await WaitForElement(group, _, options=WaitOptions(timeout=5_000)).run(page)
    assert found.is_ok() and found.ok is not None
    assert (await found.ok.text()).ok == "ok"

    gone = SelectorGroup("gone", css(".never"), xpath("//aside"))
    hidden = await WaitForElement(
        gone, _, options=WaitOptions(timeout=1_000, state="detached")
    ).run(page)
    assert hidden.ok is None


async def test_frames_and_positional_clicks(browser_session: BrowserSession) -> None:
    page = browser_session.page
    inner = escape(
        "<button id=b onclick=\"this.textContent='clicked'\" "
        "style='width:120px;height:40px'>press</button>",
        quote=True,
    )
    await Navigate(_, html(f'<iframe id=f srcdoc="{inner}"></iframe>')).run(page)
    await asyncio.sleep(0.2)

    frame = await ContentFrame("#f", _).run(page)
    assert frame.is_ok()
    clicked = await Click("#b", _, options=ClickOptions(position=(10, 10))).run(
        frame.ok
    )
    assert clicked.is_ok()
    assert (await GetText("#b", _).run(frame.ok)).ok == "clicked"

    not_a_frame = await ContentFrame("body", _).run(page)
    assert isinstance(not_a_frame.error, ElementNotFoundError)


CLICK_PAGE = html(
    '<p id=count>0</p><button id=next onclick="setTimeout(() => {'
    "const c = document.querySelector('#count'); c.textContent = +c.textContent + 1"
    '}, DELAY)">next</button>'
)


async def test_await_change_waits_for_the_dom_swap(
    browser_session: BrowserSession,
) -> None:
    page = browser_session.page
    await Navigate(_, CLICK_PAGE.replace("DELAY", "150")).run(page)

    next_page = await_change(
        Click("#next", _), probe=GetText("#count", _), timeout_ms=2_000, interval_ms=20
    )
    advanced = await (next_page >> GetText("#count", _)).run(page)
    assert advanced.ok == "1"


async def test_await_change_times_out_when_nothing_changes(
    browser_session: BrowserSession,
) -> None:
    page = browser_session.page
    await Navigate(_, html("<p id=count>0</p><button id=next>noop</button>")).run(page)
    stuck = await_change(
        Click("#next", _), probe=GetText("#count", _), timeout_ms=100, interval_ms=20
    )
    assert isinstance((await stuck.run(page)).error, ChangeTimeoutError)
    assert isinstance(
        (await retry(stuck, attempts=2, on=BrowserTimeoutError).run(page)).error,
        ChangeTimeoutError,
    )


async def test_in_new_page_always_closes_pages(browser_session: BrowserSession) -> None:
    context = browser_session.context
    environment = browser_session.environment
    urls = [html(f"<h1>{n}</h1>") for n in range(4)]

    titles = await traverse_parallel(in_new_page(GetText("h1", _)), limit=2).run(
        urls, environment=environment
    )
    assert titles.ok == ["0", "1", "2", "3"]
    assert len((await context.pages()).ok) == 1

    async def slow_or_fail(text: str) -> str:
        if text == "0":
            raise RuntimeError("first fails")
        await asyncio.sleep(5)
        return text

    from fp_ops import operation

    failing = in_new_page(GetText("h1", _) >> operation(slow_or_fail))
    outcome = await traverse_parallel(failing, limit=4).run(
        urls, environment=environment
    )
    assert outcome.is_error()
    assert len((await context.pages()).ok) == 1


async def test_isolated_pages_get_and_close_their_own_context(
    browser_session: BrowserSession,
) -> None:
    environment = browser_session.environment
    read_cookie = in_new_page(
        Navigate(_, html("<p>x</p>")) >> GetText("p", _), isolated=True
    )
    assert (await read_cookie.run(html("<p>x</p>"), environment=environment)).ok == "x"

    context = await CreateContext(_).run(None, environment=environment)
    assert context.is_ok()
    assert (await context.ok.close()).is_ok()
