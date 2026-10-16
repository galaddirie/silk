# Silk

Silk is a typed browser-automation and scraping library built on FP-Ops 0.3.1.
Browser actions are immutable unary operations: they consume one explicit focus
value, use stable capabilities from a read-only environment, and return an
FP-Ops `Result` when run.

Silk currently provides a Playwright-backed Chromium adapter and supports
Python 3.11 through 3.13.

## Installation

Install Silk and the Chromium browser binary it drives:

```bash
python -m pip install silk-scraper
python -m playwright install chromium
```

Linux CI images normally also need Playwright's operating-system packages:

```bash
python -m playwright install --with-deps chromium
```

## Quick start

```python
import asyncio

from fp_ops import Operation, _

from silk.actions.elements import GetInnerText
from silk.actions.navigation import Navigate
from silk.browsers.models import BrowserOptions, Page
from silk.browsers.sessions import BrowserSession


pipeline: Operation[Page, str] = (
    Navigate(_, "https://example.com")
    .then(GetInnerText("h1", _))
)


async def main() -> None:
    options = BrowserOptions(headless=True)
    async with BrowserSession(options=options) as session:
        result = await pipeline.run(
            session.page,
            environment=session.environment,
        )
        if result.is_error():
            raise result.error
        print(result.ok)


asyncio.run(main())
```

`BrowserSession` owns the driver, initial browser context, and initial page.
The pipeline receives the page as ordinary input and the session's stable
capabilities through the FP-Ops `Environment`; neither is inferred.

## Typed unary composition

Every public action is a construction-time operation template. A template call
must contain exactly one direct `fp_ops._` placeholder. The placeholder selects
the operation's unary input, while every other argument is configuration
captured when the operation is constructed.

```python
from fp_ops import Operation, _

from silk.actions.elements import ElementScope, GetInnerText


read_heading: Operation[ElementScope, str] = GetInnerText("h1", _)
```

Compose operations left to right with `.then`; `.run` always receives exactly
one value:

```python
result = await first.then(second).run(value, environment=environment)
```

Templates keep each meaningful positional operand flexible. For example, both
ends of a drag can be pipeline data:

```python
Drag(_, cart)  # source is the input
Drag(cart, _)  # target is the input
```

Element extraction provides the same flexibility:

```python
GetInnerText(_, parent)    # selector or element target is the input
GetInnerText(selector, _)  # page or element scope is the input
```

Each call still has exactly one construction-time placeholder. Configuration
is never appended when the operation runs.

## Focus and capabilities

Silk separates changing browser focus from stable session capabilities.

| Role | Public values | How it flows |
|---|---|---|
| Changing focus | `Page`, `BrowserContext`, `ElementHandle`, lists of elements | Ordinary operation input and output |
| Stable context creation | `DRIVER` / `BrowserDriverCapability` | `session.environment` |
| Stable session identity | `BROWSER_SESSION` / `BrowserSessionInfo` | `session.environment` |
| Browser launch configuration | `BROWSER_OPTIONS` / `BrowserOptionsCapability` | Exact immutable launch value |

Creating or selecting a page returns that page. Querying returns an element or
an ordered element list. No action changes hidden focus, and returning a
browser value never changes the environment.

Use the typed environment keys when defining a capability-aware operation:

```python
from fp_ops import Result, environment_result_operation_template

from silk.browsers.capabilities import DRIVER, BrowserDriverCapability
from silk.browsers.models import BrowserContext, BrowserContextOptions


@environment_result_operation_template(DRIVER)
async def isolated_context(
    options: BrowserContextOptions,
    capability: BrowserDriverCapability,
) -> Result[BrowserContext, Exception]:
    return await capability.new_context(options)
```

`BrowserDriverCapability` deliberately exposes neither the adapter handle nor
an umbrella `close`. Context creation is coordinated by its owning
`BrowserSession`; close the browser through `BrowserSession.close`,
`close_fail_fast`, or `close_all_settled`. A capability retained after cleanup
returns `BrowserSessionNotStartedError` from `new_context`.

## Immutable configuration

Configuration is explicit and purpose-built:

- `BrowserOptions` configures only the installed Chromium process: headless
  mode, launch timeout, immutable command-line arguments, and an optional
  `BrowserLaunchProxy` endpoint.
- `NavigateOptions` is the frozen URL-navigation record and uniquely owns the
  optional HTTP referer. `NavigationOptions` contains only timeout/load-state
  policy for history, reload, and future navigation waits. `WaitOptions` is
  likewise restricted to selector-wait behavior.
- `ClickOptions`, `DoubleClickOptions`, `FillOptions`, and `TypeTextOptions`
  are frozen action-specific values.
- `DragOptions` is a frozen value for element-to-element movement and offsets.
- `BrowserContextOptions` is a deeply immutable isolated-context record. It
  composes `BrowserViewport`, `BrowserProxy`, `BrowserHttpHeaders`, and tuple
  permissions instead of retaining mutable dictionaries or lists.
- selectors and template operands are snapshotted during construction, so
  later mutation of caller-owned configuration cannot retarget an action.

```python
from silk.actions.navigation import NavigateOptions, NavigationOptions
from silk.browsers.models import (
    BrowserContextOptions,
    BrowserHttpHeaders,
    BrowserLaunchProxy,
    BrowserOptions,
    BrowserProxy,
    BrowserViewport,
)


launch_options = BrowserOptions(
    headless=True,
    timeout=10_000,
    args=("--disable-gpu",),
    proxy=BrowserLaunchProxy(server="http://proxy.example:8080"),
)
navigate_options = NavigateOptions(
    timeout=10_000,
    wait_until="domcontentloaded",
    referer="https://example.com/source",
)
history_options = NavigationOptions(
    timeout=10_000,
    wait_until="domcontentloaded",
)
context_options = BrowserContextOptions(
    viewport=BrowserViewport(width=1280, height=720),
    permissions=("geolocation",),
    extra_http_headers=BrowserHttpHeaders({"x-silk": "typed"}),
    proxy=BrowserProxy(server="http://proxy.example:8080"),
    navigation_timeout=10_000,
    ignore_https_errors=False,
    java_script_enabled=True,
)
```

This keeps configuration separate from live browser handles. Pages, contexts,
and elements retain identity when a template snapshots them because they are
side-effecting focus values, not configuration records.

## Public modules

- `silk.actions.browser`, `.navigation`, `.elements`, and `.input` contain the
  typed operation templates and their action-specific configuration values.
- `silk.browsers.models` defines nominal focus types and immutable browser
  configuration; `.capabilities` defines environment keys; `.sessions` owns
  lifecycle. The Playwright adapter is an internal session implementation.
- `silk.selectors` contains immutable selectors, and `silk.errors` contains
  Silk's public domain errors.
- FP-Ops owns `Operation`, `Result`, `_`, composition, traversal, object
  construction, and policy combinators.

## Action surface

PascalCase distinguishes Silk's DSL actions from ordinary Python functions;
each action below constructs a typed unary operation.

| Area | Actions |
|---|---|
| Browser lifecycle | `CreateContext`, `NewPage`, `Pages`, `PageById`, `ClosePage`, `CloseContext` |
| Navigation and page data | `Navigate`, `GoBack`, `GoForward`, `Reload`, `WaitForNavigation`, `CurrentUrl`, `Title`, `Content`, `Screenshot`, `ScreenshotTo`, `Evaluate`, `EvaluateWith` |
| Elements and extraction | `Query`, `RequireElement`, `QueryAll`, `GetText`, `GetInnerText`, `GetAttribute`, `RequireAttribute`, `GetHtml`, `ElementExists`, `WaitForElement`, `ExtractTable` |
| Pointer, keyboard, and forms | `Click`, `DoubleClick`, `Fill`, `TypeText`, `SelectValue`, `SelectText`, `ScrollIntoView`, `ScrollTo`, `MouseMove`, `MouseMoveTo`, `MouseDown`, `MouseUp`, `KeyPress`, `KeyDown`, `KeyUp`, `Drag` |

`Query` returns `None` only when no selector matches. `RequireElement` turns
that absence into `ElementNotFoundError`. Similarly, `GetAttribute` returns a
successful `None` for an absent attribute, while `RequireAttribute` returns
`AttributeNotFoundError`.

Selectors may be CSS strings or immutable `Selector`/`SelectorGroup` values.
A selector group tries its entries in declaration order, but a browser error is
preserved as an error rather than mistaken for a missing element.

`WaitForNavigation` arms a wait for the next main-frame navigation and then
waits for its configured load state. It does not merely inspect the current
page's already-reached load state.

## Object and collection pipelines

FP-Ops supplies typed object construction and traversal. The complete public
books example builds an immutable model for every product card:

```python
from dataclasses import dataclass

from fp_ops import Operation, _, build, traverse

from silk.actions.elements import ElementScope, GetText, QueryAll, RequireAttribute
from silk.actions.navigation import Navigate
from silk.browsers.models import Page


@dataclass(frozen=True, slots=True)
class Book:
    title: str
    price: str


extract_book: Operation[ElementScope, Book] = build(
    {
        "title": RequireAttribute("h3 > a", _, attribute="title"),
        "price": GetText("p.price_color", _),
    },
    Book,
)

books: Operation[Page, list[Book]] = (
    Navigate(_, "https://books.toscrape.com/")
    .then(QueryAll("article.product_pod", _))
    .then(traverse(extract_book))
)
```

See the
[complete runnable example](https://github.com/galaddirie/silk/blob/main/examples/books_to_scrape.py).

## Error policies and inspectable causes

Once `.run` begins, ordinary exceptions stay in the operation's
`Result[..., Exception]` error channel. Cancellation and other
`BaseException` subclasses propagate.

The default policies are deliberately fail-fast:

- `build` stops at the first failed field and returns `BuildFieldError`.
- `traverse` stops at the first failed item and returns `TraversalItemError`.
- `fanout_parallel` cancels and joins unfinished siblings after a failure.

The wrappers retain the original browser exception. `BuildFieldError` exposes
`.field` and `.cause`; `TraversalItemError` exposes `.index` and `.cause`; both
also preserve Python exception chaining through `.__cause__`. A failed books
pipeline therefore remains inspectable as:

```text
TraversalItemError(index=...)
  -> BuildFieldError(field=...)
     -> original browser exception
```

Choose a different policy only by using a truthfully named combinator:

- all-settled: `build_all_settled`, `traverse_all_settled`,
  `fanout_all_settled`;
- lossy: `build_lossy`, `traverse_lossy`, `filter_best_effort`;
- retry: `retry`, whose `attempts` count includes the first call and whose final
  error is retained;
- bounded parallel: `fanout_parallel`, `traverse_parallel`;
- sequential fail-fast: `build`, `traverse`, `filter_operation`.

All-settled operations retain one `Result` per field, item, or branch. Lossy
operations deliberately omit failed values. These return shapes are distinct,
so policy is visible in both the name and the type.

Browser cleanup follows the same explicit naming. `BrowserSession.close`
attempts every acquired resource before raising retained cleanup failure(s),
`close_fail_fast` joins an in-flight resource close but stops after the first
failure, interruption, or observed caller cancellation, leaving later
ownership available for an explicit retry, and
`close_all_settled` returns every ordinary cleanup failure with its cause.
Starting a session twice, or before a failed close has been retried
successfully, raises without replacing the session's existing ownership.

## Shared `DRIVER` concurrency contract

Parallel FP-Ops combinators reuse the exact operation input, `Environment`, and
`DRIVER` capability for every branch. They do not clone a context, page,
element, or capability. A `limit` bounds active tasks; it does not create
browser isolation or serialize access to shared focus. The session-owned
capability does serialize context acquisition with session cleanup so browser
ownership cannot change underneath either operation.

Consequently:

- use bounded limits for browser work;
- use separate pages or contexts when the underlying workflow requires
  isolation;
- avoid concurrent state-changing operations on the same page or element
  unless the browser adapter explicitly guarantees that interaction;
- expect declaration-order results even though effect completion order is not
  specified;
- expect fail-fast cancellation to be best effort because an external browser
  effect may finish before cancellation is observed.

The environment mapping is read-only. Its browser capability is an immutable,
session-owned context factory; raw adapter lifecycle control is not exposed.

## Development gates

Install the locked development environment and Chromium from clean caches,
then run the same core gates as CI:

```bash
poetry cache clear pypi --all --no-interaction
poetry install --with dev --no-interaction
poetry run playwright install --with-deps chromium
poetry run pre-commit run --all-files
poetry check --lock --strict
poetry run python -m pytest tests -v
poetry run mypy
poetry run pyright
poetry run python tests/typecheck/check_bad_fixtures.py --all-python-versions
poetry build --clean
```

`pre-commit run --all-files` is the exact repository quality gate used by CI.
The locked development environment pins the runner; `.pre-commit-config.yaml`
pins every hook and Flake8 plugin used by that gate.

Every deliberately invalid expression in `tests/typecheck/*_bad.py` has a
stable `# typecheck-case: ...` marker. The negative harness associates that
marker with the following AST statement, requires a pinned rule and semantic
message from both strict mypy and pinned Pyright, and rejects diagnostics
outside marked statements. After an intentional public typing change, refresh
the marker-keyed artifact only by running:

```bash
poetry run python tests/typecheck/check_bad_fixtures.py --write-contract
```

That command observes both Python 3.11 and 3.13 targets and fails unless every
case has a shared semantic diagnostic. Review the generated rule/message pair
for each intentionally changed case; secondary checker cascades are confined
and counted but are not blessed into the contract.

The runtime suite includes local browser integration tests and the real
`https://books.toscrape.com/` pipeline. CI also installs the built wheel into a
fresh virtual environment outside the checkout and repeats a real Chromium
public-pipeline smoke.

## License

Silk is available under the MIT License.
