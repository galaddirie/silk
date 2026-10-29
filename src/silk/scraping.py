# pyright: strict
"""Scraping flows built from FP-Ops control nodes: isolated pages and change waits.

Both are ordinary operations: their environment needs are visible to
preflight, and they compose with ``retry``, ``loop`` and the traversals.
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from math import ceil
from typing import TypeVar

from fp_ops import (
    Continue,
    EnvKey,
    Operation,
    Stop,
    _,
    bracket,
    branch,
    constant,
    from_environment,
    identity,
    loop,
    operation,
    passthrough,
    provide,
    sleep,
)

from silk.actions.browser import CloseContext, ClosePage, CreateContext, OpenPage
from silk.actions.navigation import NavigateOptions
from silk.browsers.models import CONTEXT, BrowserContext, Page
from silk.errors import ChangeTimeoutError

B = TypeVar("B")
S = TypeVar("S")
T = TypeVar("T")
U = TypeVar("U")


def _first(pair: tuple[T, U]) -> T:
    return pair[0]


def _second(pair: tuple[T, U]) -> U:
    return pair[1]


def in_new_page(
    body: Operation[Page, B],
    *,
    isolated: bool = False,
    options: NavigateOptions | None = None,
) -> Operation[str, B]:
    """Open the input URL in a new page, run ``body`` on it, and always close it.

    The page opens in the environment's ``CONTEXT`` (the session's context).
    With ``isolated=True`` it gets a fresh context of its own, created with the
    session's context options and closed afterwards: separate cookies and
    storage per item. Closing also happens when a fail-fast sibling cancels it::

        threads = traverse_all_settled(in_new_page(crawl_thread), limit=4)
    """

    page_scope: Operation[str, B] = bracket(
        OpenPage(_, options=options), body, ClosePage(_)
    )
    if not isolated:
        return page_scope

    keep: Operation[str, str] = identity()
    new_context: Operation[object, BrowserContext] = constant(None) >> CreateContext(_)
    url_of: Operation[tuple[str, BrowserContext], str] = operation(_first)
    context_of: Operation[tuple[str, BrowserContext], BrowserContext] = operation(
        _second
    )
    return bracket(
        keep & new_context,
        provide(CONTEXT, context_of, url_of >> page_scope),
        context_of >> CloseContext(_),
    )


@dataclass(frozen=True, slots=True)
class _Observed:
    value: Hashable


def await_change(
    action: Operation[S, object],
    *,
    probe: Operation[S, Hashable],
    timeout_ms: int = 10_000,
    interval_ms: int = 100,
    attempts: int = 1,
) -> Operation[S, S]:
    """Run ``action`` and wait until ``probe`` reads a different value.

    This is the stale-DOM guard for "click Next, then read": probe something
    the action must change (the first card's id, the card count, the URL), and
    reads afterwards see the new content.

    ``attempts`` repeats the action when nothing changed in time. Each attempt
    first re-checks against the value from *before the first attempt*, so a
    change that is visible by then is never followed by another action. (An
    effect that lands even later is indistinguishable from a lost click; pick a
    ``timeout_ms`` longer than the slowest expected update.) Gives up with
    ``ChangeTimeoutError``.
    """

    if timeout_ms < 0 or interval_ms < 1 or attempts < 1:
        raise ValueError(
            "await_change needs timeout_ms >= 0, interval_ms >= 1, attempts >= 1"
        )

    before = EnvKey("silk.await_change.before", _Observed)
    keep: Operation[S, S] = identity()

    def differs(pair: tuple[Hashable, _Observed]) -> bool:
        return pair[0] != pair[1].value

    changed: Operation[S, bool] = (probe & from_environment(before)).map(differs)

    pause: Operation[S, S] = sleep(interval_ms / 1000)
    poll: Operation[S, Continue[S] | Stop[S]] = branch(
        changed,
        keep.map(Stop),
        pause.map(Continue),
    )
    polls = max(1, ceil(timeout_ms / interval_ms))
    attempt: Operation[S, Continue[S] | Stop[S]] = branch(
        changed,
        keep.map(Stop),
        passthrough(action) >> loop(poll, max_steps=polls) >> keep.map(Continue),
    )

    def timed_out(_state: S) -> S:
        raise ChangeTimeoutError(
            f"nothing changed within {timeout_ms} ms after {attempts} attempt(s)"
        )

    settled: Operation[S, S] = branch(changed, keep, operation(timed_out))
    observe: Operation[S, _Observed] = probe.map(_Observed)
    return provide(before, observe, loop(attempt, max_steps=attempts) >> settled)


__all__ = ["await_change", "in_new_page"]
