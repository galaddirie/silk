<p align="center">
  <img src="https://github.com/user-attachments/assets/49798c93-66b4-448b-8450-0d9233f915e3" alt="Silk">
</p>
<p align="center">
    <em><b>Silk</b> — a declarative, fully typed web scraping library for building resilient browser automations in Python.</em>
</p>

---
[![PyPI version](https://img.shields.io/badge/pypi-v0.4.1-blue.svg)](https://pypi.org/project/silk-scraper/)
[![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/silk-scraper/)
[![PyPI Downloads](https://static.pepy.tech/badge/silk-scraper)](https://pepy.tech/projects/silk-scraper)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type check: mypy](https://img.shields.io/badge/type%20check-mypy%20strict-blue)](https://github.com/python/mypy)
[![Type check: pyright](https://img.shields.io/badge/type%20check-pyright%20strict-blue)](https://github.com/microsoft/pyright)

Silk lets you write elegant, resilient scrapers as small typed pipelines. You
describe **what** to extract; Silk handles the browser.

```python
book = (
    Navigate(_, "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")
    >> (GetText("h1", _) & GetText("p.price_color", _) & GetText("table td", _))
)
# Operation[Page, tuple[str, str, str]] — three reads, run concurrently
# Ok(('A Light in the Attic', '£51.77', 'a897fe39b1053632'))
```

## Key Features

- **Composable DSL**: Chain with `>>`, run in parallel with `&`, fall back with `|`.
- **Errors as values**: Every run returns `Ok(value)` or `Error(exception)`; nothing is swallowed.
- **Typed end to end**: Pipelines are `Operation[In, Out]`, checked by strict mypy and Pyright.
- **Immutable by design**: Actions are frozen values with no hidden browser state.
- **Resilient**: Selector fallback groups, `retry`, recovery, and explicit failure policies.
- **Schema-first extraction**: Build dataclasses, Pydantic models, or dicts straight from the page.

## First-Class Composition

Silk treats composition as a **first-class citizen**:

- **Actions as values**: Browser actions are immutable operations you can store, pass, and combine.
- **Intuitive operators**: Compose with `>>`, `&`, and `|` for pipelines that read top to bottom.
- **Composition is associative**: `(a >> b) >> c` is the same pipeline as `a >> (b >> c)`.
- **Modular architecture**: Complex workflows emerge from small, reusable, independently tested pieces.

| Operator | Name | Meaning |
|---|---|---|
| `a >> b` | then | Feed `a`'s output into `b` |
| `a & b` | fan out | Run `a` and `b` on the same input concurrently, collect `(a, b)` |
| `a \| b` | or else | If `a` fails, run `b` on the original input |

```python
from fp_ops import _

from silk.actions.elements import GetText, RequireAttribute, RequireElement
from silk.actions.navigation import Navigate

first_card = RequireElement("article.product_pod", _)
title = RequireAttribute("h3 > a", _, attribute="title")
price = GetText(".sale-price", _) | GetText("p.price_color", _)

first_book = (
    Navigate(_, "https://books.toscrape.com/")
    >> first_card
    >> (title & price)
)
# Operation[Page, tuple[str, str]]
```

### Developer Experience

Actions are type-safe operations (`Operation[In, Out]`). Describe the shape;
Silk does the work:

```python
from dataclasses import dataclass

from fp_ops import _, build, traverse

from silk.actions.elements import GetText, QueryAll, RequireAttribute
from silk.actions.navigation import Navigate


@dataclass(frozen=True, slots=True)
class Book:
    title: str
    price: str


extract_book = build(  # dataclasses, Pydantic models, any class, or a plain dict
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText("p.price_color", _),
    },
    Book,
)

books = (
    Navigate(_, "https://books.toscrape.com/")  # load the page
    >> QueryAll("article.product_pod", _)       # list[ElementHandle]
    >> traverse(extract_book)                   # list[Book]
)
# Operation[Page, list[Book]]
```

Why it feels great:

- **Actions as values**: Drop actions directly into a schema, with no glue code or lambdas.
- **Types flow through**: Your editor knows `books` produces `list[Book]` before it runs.
- **Honest failures**: A failed field reports *which* item and *which* field, with the original browser error attached.

Silk also provides utilities such as selector groups for handling fallbacks:

```python
from silk.selectors import SelectorGroup, css, xpath

title_selector = SelectorGroup(
    "book_title",
    css("h3 > a[title]"),
    css(".product_pod h3 a"),
    xpath("//article[contains(@class, 'product_pod')]//h3/a"),
)
price_selector = SelectorGroup(
    "book_price",
    css("p.price_color"),
    xpath("//p[contains(@class, 'price')]"),
)

extract_book = build(
    {
        "title": RequireAttribute(title_selector, _, attribute="title"),
        "price": GetText(price_selector, _),
    },
    Book,
)
```

### Declarative API

Silk embraces **declarative programming** that focuses on **what** to
accomplish, not **how**:

```python
# Imperative: HOW to read the first book
await page.goto("https://books.toscrape.com/")
card = await page.query_selector("article.product_pod")
if card is None:
    raise LookupError("no product card")
link = await card.query_selector("h3 > a")
title = await link.get_attribute("title") if link else None
price_element = await card.query_selector("p.price_color")
price = await price_element.text_content() if price_element else None

# Declarative: WHAT to read with Silk
first_book = (
    Navigate(_, "https://books.toscrape.com/")
    >> RequireElement("article.product_pod", _)
    >> (RequireAttribute("h3 > a", _, attribute="title") & GetText("p.price_color", _))
)
```

Missing elements and attributes become explicit `ElementNotFoundError` and
`AttributeNotFoundError` values instead of `None` checks scattered through
your code.

## Installation

```bash
pip install silk-scraper
python -m playwright install chromium
```

Linux CI images usually also need Playwright's system packages:

```bash
python -m playwright install --with-deps chromium
```

## Quick Start

```python
import asyncio

from fp_ops import _

from silk.actions.elements import GetText, RequireAttribute
from silk.actions.navigation import Navigate
from silk.browsers.models import BrowserOptions
from silk.browsers.sessions import BrowserSession

pipeline = (
    Navigate(_, "https://books.toscrape.com/")
    >> (
        GetText("li.current", _).map(str.strip)
        & RequireAttribute("h3 > a", _, attribute="title")
    )
)


async def main() -> None:
    async with BrowserSession(options=BrowserOptions(headless=True)) as session:
        result = await pipeline.run(session.page, environment=session.environment)

        if result.is_ok():
            page_label, first_title = result.ok
            print(f"{page_label}: {first_title}")  # Page 1 of 50: A Light in the Attic
        else:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
```

`BrowserSession` owns the browser, its first context, and its first page. The
page goes in as the pipeline's input; the browser is shared through the
read-only `session.environment`.

## Core Concepts

### Actions

Actions are the building blocks of your scraping logic. Each action:

- is an immutable, typed `Operation[In, Out]` built when you call it;
- takes exactly one input, marked by the `_` placeholder;
- returns a `Result`, either `Ok(value)` or `Error(exception)`, when run.

The `_` decides which argument is the pipeline input. Everything else is
configuration fixed at construction:

```python
GetText("h1", _)           # input: the page or element to search in
GetText(_, card)           # input: the selector or element to read
Drag(_, basket)            # input: the element being dragged
Drag(book, _)              # input: the drop target
```

Run any pipeline with exactly one value:

```python
result = await pipeline.run(session.page, environment=session.environment)
```

### Sequential Operations (`>>`)

`>>` feeds each step's output into the next. Actions move the focus forward:
querying returns an element, so the next step is scoped to it.

```python
add_first_book_to_basket = (
    Navigate(_, "https://books.toscrape.com/")   # Page
    >> RequireElement("article.product_pod", _)  # that book's card
    >> Click("button.btn-primary", _)            # its own "Add to basket"
)
```

Plain Python functions join a pipeline with `@operation`:

```python
from fp_ops import operation


@operation
def parse_price(text: str) -> float:
    return float(text.removeprefix("£"))


price = GetText("p.price_color", _) >> parse_price  # Operation[ElementScope, float]
```

### Parallel Operations (`&`)

`&` runs branches concurrently on the **same input** and collects their
results into one flat tuple, in declaration order:

```python
summary = (
    GetText("form.form-horizontal strong", _).map(int)  # total results
    & GetText("li.current", _).map(str.strip)           # pager label
    & QueryAll("article.product_pod", _).map(len)       # books on this page
)
# Operation[ElementScope, tuple[int, str, int]] -> Ok((1000, 'Page 1 of 50', 20))
```

`a & b & c` yields `(a, b, c)`. A branch that itself returns a tuple stays a
single value, and `a & (b & c)` nests as `(a, (b, c))`. If any branch fails,
the others are cancelled and the error is returned.

For truly independent work, give each branch its own page:

```python
from fp_ops import Operation

from silk.actions.browser import NewPage
from silk.browsers.models import BrowserContext

CATALOGUE = "https://books.toscrape.com/catalogue"


def book_title(slug: str) -> Operation[BrowserContext, str]:
    return NewPage(_) >> Navigate(_, f"{CATALOGUE}/{slug}/index.html") >> GetText("h1", _)


titles = (
    book_title("a-light-in-the-attic_1000")
    & book_title("tipping-the-velvet_999")
    & book_title("soumission_998")
)

result = await titles.run(session.context, environment=session.environment)
# Ok(('A Light in the Attic', 'Tipping the Velvet', 'Soumission'))
```

### Fallback Operations (`|`)

`|` tries an alternative, with the **original input**, when the first
operation fails:

```python
price = GetText(".sale-price", _) | GetText(".regular-price", _) | GetText("p.price_color", _)
```

Fallbacks combine with every other operator. Each strategy below is a whole
pipeline, and the first one to succeed wins:

```python
from fp_ops import constant

page_label = GetText("li.current", _).map(str.strip) | constant("Page 1 of 1")

title = (
    RequireAttribute("h3 > a", _, attribute="title")      # full title attribute
    | GetText("h3 > a", _)                                # truncated link text
    | constant("Untitled")                                # last resort
)
```

`|` gives up on *any* failure, including browser errors. Use selector groups
when only the selector should vary, and `|` when the whole strategy should.

## Resilience

Every policy has a truthful name, so failure behavior is visible in the code:

```python
from fp_ops import default_on_error, recover, retry

price = (
    retry(GetText("p.price_color", _), attempts=3, backoff=0.5)  # 3 tries in total
    | GetText(".price", _)
    | constant("unknown")
)

title = default_on_error(GetText("h1", _), "untitled")
length = recover(GetText("h1", _).map(len), lambda error: 0)
```

| Work | Fail fast | Keep every result | Keep successes |
|---|---|---|---|
| Parallel branches | `a & b` / `fanout_parallel` | `fanout_all_settled` | — |
| Collection items | `traverse` / `traverse_parallel` | `traverse_all_settled` | `traverse_lossy` |
| Object fields | `build` | `build_all_settled` | `build_lossy` |
| Predicates | `filter_operation` | — | `filter_best_effort` |

Failures keep their causes. If one field of one book fails, the error reads:

```text
TraversalItemError(index=3)
  -> BuildFieldError(field="title")
     -> original browser exception
```

## Collections and Objects

Silk's collection and object helpers come from
[FP-Ops](https://github.com/galaddirie/fp-ops) and work directly with actions:

```python
from fp_ops import filter_each, traverse, traverse_parallel


def under_20(price: float) -> bool:
    return price < 20


cards = QueryAll("article.product_pod", _)

books = cards >> traverse_parallel(extract_book, limit=5)               # list[Book]
prices = cards >> traverse(GetText("p.price_color", _) >> parse_price)  # list[float]
bargains = prices >> filter_each(under_20)                              # list[float]
```

`build` constructs any class (dataclasses, Pydantic models, …) or, without
one, a plain `dict`. Collection results always preserve input order.

## Real-World Scraping

### Optional fields, the element itself, and links

Real pages leave fields out. `optional` turns "nothing matched" into `None`
while a browser failure stays an error; `SELF` reads the focused element itself;
`GetUrl` resolves links the way the browser does:

```python
from silk.actions.elements import GetAttribute, GetText, GetUrl, optional
from silk.selectors import SELF

extract_review = build(
    Review,                                         # keyword form: fields type-check one by one
    review_id=GetAttribute(SELF, _, attribute="data-review-id"),
    title=GetText("h3", _),
    location=optional(GetText(".location", _)),     # None when absent
    permalink=GetUrl("a.permalink", _),             # absolute, honours <base href>
)
```

### Crawling pages

FP-Ops' `loop` repeats a step until it returns `Stop`, in constant stack
space. `derive` passes a value read from the page (here, the next link) to the
action that navigates it:

```python
from fp_ops import continue_if, derive, loop, passthrough, retry
from silk.errors import BrowserTimeoutError, NavigationError

NEXT = SelectorGroup("next", css("a[rel=next]"), xpath("//a[normalize-space()='Next']"))

follow_next = retry(
    Navigate(_, derive(GetUrl(NEXT, _))),
    attempts=3,
    on=(BrowserTimeoutError, NavigationError),     # only browser hiccups are retried
)
crawl = Navigate(_, START) >> loop(
    passthrough(reviews_on_page >> save(_)) >> continue_if(ElementExists(NEXT, _), follow_next),
    max_steps=200,
)
```

A failed page returns `LoopStepError(step, state, cause)`. Pages saved before
it stay saved.

For "click Next" or "Load more" on the same tab, wait for the click to take
effect instead of sleeping:

```python
from silk.scraping import await_change

next_page = await_change(
    passthrough(Click(NEXT, _)),
    probe=GetAttribute(".review", _, attribute="data-id"),  # the first card changes
    attempts=2,                    # re-checks before clicking again: never double-advances
)
```

### Isolated pages, request blocking, frames

```python
from silk.scraping import in_new_page

# Every thread in its own page (or isolated=True: its own context), always closed.
threads = traverse_all_settled(in_new_page(crawl_thread), limit=4).map(partition)

options = BrowserContextOptions(
    blocking=RequestBlocking(resource_types=frozenset({"image", "font", "media"})),
)

checkbox = ContentFrame("iframe#challenge", _) >> Click("input", _, options=ClickOptions(position=(10, 10)))
```

### Errors you can act on

Playwright and Patchright failures arrive as `BrowserTimeoutError`,
`NavigationError`, `TargetClosedError` or `BrowserError`, with the native error
as `__cause__`. Lookups that find nothing are `NotFoundError`s. Policies can
therefore target exactly what they mean: `retry(..., on=BrowserTimeoutError)`,
`default_on_error(..., on=NotFoundError)`.

### HTTP without (or through) the browser

`silk.http` makes the transport an environment dependency, so one pipeline can
fetch through httpx, through the browser context (sharing its cookies), or
with an in-page `fetch()` for bot-protected APIs:

```python
from silk.http import HTTP, FetchJson, HttpRequest, HttpxClient, PageFetchClient

reviews_page = FetchJson(_).map(ReviewsPage.model_validate)       # Operation[HttpRequest | str, ReviewsPage]

environment = session.environment                                  # HTTP = the context's request API
environment = environment.with_value(HTTP, PageFetchClient(session.page))  # or browser fetch()
```

### Static HTML: one pipeline, two transports

`silk.static` (`pip install "silk-scraper[static]"`) implements `Page` and
`ElementHandle` over parsed HTML, so the same extraction runs without a
browser, and in fast offline tests:

```python
from silk.static import ParseHtml, SnapshotPage, StaticPage

page_reviews = QueryAll(".review", _) >> traverse(extract_review)

# HTML fetched over HTTP, no browser at all:
from_http = Fetch(_) >> ParseHtml(_) >> page_reviews

# A live page read in one round trip, then extracted in-process:
from_browser = Navigate(_, url) >> SnapshotPage(_) >> page_reviews

# Tests:
await page_reviews.run(StaticPage.from_html(FIXTURE, url="https://example.com/p/1"))
```

CSS (via cssselect) and XPath behave as in Chromium (XPath starting with `/`
is relative to the element, like Playwright). Interactions, navigation and
Playwright-only selector engines (`text=`, `:has-text`, …) return
`UnsupportedOperationError`. `inner_text` approximates layout from tag names,
not stylesheets.

## Creating Custom Actions

Turn any function into an action with a configurable template. The `_` marks
the input, just like Silk's own actions:

```python
from fp_ops import operation_template


@operation_template
def strip_prefix(prefix: str, text: str) -> str:
    return text.removeprefix(prefix)


price = GetText("p.price_color", _) >> strip_prefix("£", _) >> parse_price
```

`result_operation_template` returns a `Result` directly, and
`environment_result_operation_template(BROWSER)` receives the running browser:

```python
from fp_ops import Result, environment_result_operation_template

from silk.browsers.models import BROWSER, Browser, BrowserContext, BrowserContextOptions


@environment_result_operation_template(BROWSER)
async def isolated_context(
    options: BrowserContextOptions,
    browser: Browser,
) -> Result[BrowserContext, Exception]:
    return await browser.new_context(options)
```

## Browser Configuration

```python
from silk.actions.navigation import NavigateOptions
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserOptions,
    BrowserProxy,
    BrowserViewport,
)
from silk.browsers.sessions import BrowserSession

options = BrowserOptions(
    headless=False,  # show the browser while debugging
    timeout=10_000,
    args=("--disable-gpu",),
    proxy=BrowserProxy(server="http://proxy.example:8080"),
)

context_options = BrowserContextOptions(
    viewport=BrowserViewport(width=1280, height=800),
    extra_http_headers={"accept-language": "en"},
    navigation_timeout=10_000,
)

navigate = Navigate(
    _,
    "https://books.toscrape.com/",
    options=NavigateOptions(wait_until="domcontentloaded"),
)

async with BrowserSession(options=options) as session:
    ...
```

Every option type is frozen. Each action has its own options (`ClickOptions`,
`FillOptions`, `WaitOptions`, `DragOptions`, …), and later changes to your own
lists or dicts can never retarget an action you already built.

## Browser Drivers

A driver launches the browser a session owns. `BrowserSession` uses Chromium
through Playwright unless you pass `driver=`. Your pipelines stay the same
whichever driver you pick.

```python
from pathlib import Path

from silk.browsers.drivers import PlaywrightDriver

BrowserSession(driver=PlaywrightDriver(browser_type="firefox"))
BrowserSession(driver=PlaywrightDriver(channel="chrome"))  # installed Google Chrome
BrowserSession(driver=PlaywrightDriver(executable_path=Path("/opt/chromium/chrome")))
```

### Stealth browsers (Patchright and other Playwright forks)

`package` loads any library that copies Playwright's `async_api`, such as
[Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python):

```bash
pip install patchright
python -m patchright install chromium
```

```python
stealth = PlaywrightDriver(package="patchright")

async with BrowserSession(driver=stealth) as session:
    result = await pipeline.run(session.page, environment=session.environment)
```

### Writing your own driver

To use another backend (Selenium, nodriver, a remote browser service, …),
subclass `BrowserDriver` and the browser interfaces in `silk.browsers`:

| Interface | You provide |
|---|---|
| `BrowserDriver` | `launch(options) -> LaunchedBrowser` |
| `LaunchedBrowser` | `new_context(options)`, `close()` |
| `BrowserContext` | `context_id`, `new_page()`, `pages()`, `close()` |
| `Page` | navigation, queries, `evaluate`, `screenshot`, mouse and keyboard |
| `ElementHandle` | queries, reads, clicks, typing, pointer moves, `drag_to` |

Abstract base classes enforce the contract: Python raises a `TypeError` that
names any method you have not implemented yet. Methods return
`Result` values instead of raising. `attempt` wraps an awaitable, and
`attempt_blocking` runs a synchronous call in a worker thread:

```python
from fp_ops import Result
from selenium import webdriver

from silk.browsers import BrowserDriver, BrowserOptions, LaunchedBrowser, Page
from silk.browsers.drivers import attempt_blocking


class SeleniumDriver(BrowserDriver):
    async def launch(self, options: BrowserOptions) -> LaunchedBrowser:
        chrome_options = webdriver.ChromeOptions()
        if options.headless:
            chrome_options.add_argument("--headless=new")
        for argument in options.args:
            chrome_options.add_argument(argument)
        native = await attempt_blocking(webdriver.Chrome, options=chrome_options)
        if native.is_error():
            raise native.error
        return SeleniumBrowser(native.ok)  # your LaunchedBrowser subclass


class SeleniumPage(Page):
    async def title(self) -> Result[str, Exception]:
        return await attempt_blocking(lambda: self._driver.title)

    ...
```

`launch` should raise if the browser cannot start. Only the session calls
`close()`; pipelines get the browser as a plain `Browser` and cannot close it.
If `launch` succeeds but the first context or page fails, the session closes
the browser before raising the error.

---

## API Reference

### Module Structure

```
silk/
├── actions/
│   ├── browser.py      # contexts and pages (CreateContext, NewPage, Pages, …)
│   ├── elements.py     # lookup and extraction (Query, GetText, ExtractTable, …)
│   ├── input.py        # pointer, keyboard, and forms (Click, Fill, Drag, …)
│   └── navigation.py   # navigation and page data (Navigate, Title, Screenshot, …)
├── browsers/
│   ├── models.py       # Browser/Page/ElementHandle interfaces, BROWSER key, options
│   ├── sessions.py     # BrowserSession, the browser lifecycle owner
│   └── drivers/        # PlaywrightDriver and helpers for custom drivers
├── selectors/          # Selector, SelectorGroup, SELF, css, xpath, text
├── scraping.py         # await_change, in_new_page
├── http.py             # HTTP capability: Fetch, FetchJson, HTTP clients
├── static.py           # StaticPage, ParseHtml, SnapshotPage ([static] extra)
└── errors.py           # NotFoundError family, BrowserError family, …
```

Composition (`>>`, `&`, `|`), `Result`, `_`, and the collection, object, and
policy combinators come from [FP-Ops](https://github.com/galaddirie/fp-ops).

### Actions

| Area | Actions |
|---|---|
| Browser | `CreateContext`, `NewPage`, `OpenPage`, `Pages`, `PageById`, `ClosePage`, `CloseContext` |
| Navigation and page data | `Navigate`, `GoBack`, `GoForward`, `Reload`, `WaitForNavigation`, `CurrentUrl`, `Title`, `Content`, `Screenshot`, `ScreenshotTo`, `Evaluate`, `EvaluateWith` |
| Elements and extraction | `Query`, `RequireElement`, `QueryAll`, `GetText`, `GetInnerText`, `GetAttribute`, `RequireAttribute`, `GetUrl`, `GetHtml`, `ElementExists`, `WaitForElement`, `ExtractTable`, `ContentFrame`, `OwnerPage`, `optional` |
| Pointer, keyboard, and forms | `Click`, `DoubleClick`, `Fill`, `TypeText`, `SelectValue`, `SelectText`, `ScrollIntoView`, `ScrollTo`, `MouseMove`, `MouseMoveTo`, `MouseDown`, `MouseUp`, `KeyPress`, `KeyDown`, `KeyUp`, `Drag` |

- `Query` returns `None` when nothing matches; `RequireElement` returns `ElementNotFoundError`.
- `GetAttribute` returns `None` for a missing attribute; `RequireAttribute` returns `AttributeNotFoundError`.
- Element actions such as `Click` and `Fill` return the element they acted on; page actions such as `KeyPress` and `Navigate` return the page.
- `WaitForNavigation` waits for the *next* main-frame navigation, not the current one.

### Selectors

- `css(value)`, `xpath(value)`, `text(value)` create a selector; plain strings are CSS.
- `SelectorGroup(name, *selectors)` tries each selector in order. A browser error stays an error and is never mistaken for "not found".

### Sharing a page

`&` and the parallel helpers give every branch the same input and browser; they
never clone a page or element. Concurrent *reads* of one page are safe. For
concurrent clicks, typing, or navigation, give each branch its own page with
`NewPage` or its own context with `CreateContext`. A `limit` bounds how many
tasks run at once, but it does not isolate them.

---

## Roadmap

- [x] Initial release with Playwright support
- [x] Improve manager ergonomics
- [x] Mapped tasks over collections (`QueryAll >> traverse(...)`)
- [x] Run multiple actions on one page ergonomically (`GetText & GetAttribute & GetHtml`)
- [x] Typed action signatures, checked by mypy and Pyright
- [x] Proxy options
- [x] Pluggable browser drivers (`BrowserSession(driver=...)`)
- [x] Patchright and other Playwright forks (`PlaywrightDriver(package=...)`)
- [ ] Selenium integration
- [ ] Puppeteer integration
- [ ] Explore more stealth options (nodriver, …)
- [ ] Support computer-using agents (browser-use, OpenAI CUA, Claude computer use)
- [ ] Enhanced caching
- [ ] Distributed scraping
- [x] Crawling building blocks (`loop`, `await_change`, `in_new_page`, request blocking)
- [ ] Rate limiting and polite scraping utilities
- [ ] Integrations with data and scraping libraries (Pandas, Scrapy, …)

## Development

```bash
poetry install --with dev
poetry run playwright install --with-deps chromium
poetry run pre-commit run --all-files
poetry run python -m pytest tests -v
poetry run mypy
poetry run pyright
poetry run python tests/typecheck/check_bad_fixtures.py --all-python-versions
```

The suite includes live Chromium tests, the real
[Books to Scrape example](examples/books_to_scrape.py), and an installed-wheel
smoke test. After an intentional public typing change, refresh the negative
type-check contract with
`poetry run python tests/typecheck/check_bad_fixtures.py --write-contract`.

## License

Silk is available under the MIT License.
