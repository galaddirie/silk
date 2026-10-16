"""Named FP-Ops policy contracts exercised through Silk browser actions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol, TypeGuard, runtime_checkable
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import (
    BuildFieldError,
    Environment,
    Error,
    Ok,
    Operation,
    Result,
    TraversalItemError,
    _,
    build,
    build_all_settled,
    build_lossy,
    environment_result_operation,
    fanout_all_settled,
    fanout_parallel,
    retry,
    traverse,
    traverse_all_settled,
    traverse_lossy,
    traverse_parallel,
)

from silk.actions.browser import CreateContext as create_context
from silk.actions.navigation import CurrentUrl as current_url, Title as title
from silk.browsers.capabilities import DRIVER, BrowserDriverCapability
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserViewport,
    Page,
)


@dataclass(frozen=True, slots=True)
class PageSummary:
    url: str
    title: str


@dataclass(frozen=True, slots=True)
class WorkItem:
    label: str


@runtime_checkable
class HasTraversalIndex(Protocol):
    @property
    def index(self) -> object: ...


@dataclass(slots=True)
class ActivityProbe:
    threshold: int
    active: int = 0
    max_active: int = 0
    inputs: list[WorkItem] = field(default_factory=list[WorkItem])
    capabilities: list[BrowserDriverCapability] = field(
        default_factory=list[BrowserDriverCapability]
    )
    started: list[str] = field(default_factory=list[str])
    stopped: list[str] = field(default_factory=list[str])
    cancelled: list[str] = field(default_factory=list[str])
    threshold_reached: asyncio.Event = field(default_factory=asyncio.Event)

    def enter(
        self,
        label: str,
        item: WorkItem,
        capability: BrowserDriverCapability,
    ) -> None:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.inputs.append(item)
        self.capabilities.append(capability)
        self.started.append(label)
        if self.active >= self.threshold:
            self.threshold_reached.set()

    def leave(self, label: str) -> None:
        self.active -= 1
        self.stopped.append(label)


DEFAULT_URL_RESULT: Result[str, Exception] = Ok("https://example.test")
DEFAULT_TITLE_RESULT: Result[str, Exception] = Ok("Example")


def is_indexed_traversal_error(
    error: Exception,
) -> TypeGuard[TraversalItemError[int]]:
    return (
        isinstance(error, HasTraversalIndex)
        and isinstance(error.index, int)
        and isinstance(error, TraversalItemError)
    )


def make_page(
    *,
    url: Result[str, Exception] = DEFAULT_URL_RESULT,
    page_title: Result[str, Exception] = DEFAULT_TITLE_RESULT,
) -> MagicMock:
    page = MagicMock(spec=Page)
    page.url = AsyncMock(return_value=url)
    page.title = AsyncMock(return_value=page_title)
    page.__copy__.return_value = page
    page.__deepcopy__.return_value = page
    return page


def driver_environment() -> tuple[MagicMock, BrowserDriverCapability, Environment]:
    driver = MagicMock()
    capability = BrowserDriverCapability(driver.new_context)
    environment = Environment().with_value(DRIVER, capability)
    return driver, capability, environment


def controlled_branch(
    label: str,
    probe: ActivityProbe,
    release: asyncio.Event,
    *,
    failure: Exception | None = None,
    finished: asyncio.Event | None = None,
) -> Operation[WorkItem, str]:
    @environment_result_operation(DRIVER)
    async def branch(
        item: WorkItem,
        capability: BrowserDriverCapability,
    ) -> Result[str, Exception]:
        probe.enter(label, item, capability)
        try:
            await release.wait()
            if failure is not None:
                return Error(failure)
            return Ok(label)
        except asyncio.CancelledError:
            probe.cancelled.append(label)
            raise
        finally:
            probe.leave(label)
            if finished is not None:
                finished.set()

    return branch


@pytest.mark.asyncio
async def test_build_policies_are_fail_fast_settled_or_explicitly_lossy() -> None:
    browser_error = RuntimeError("browser target closed")

    fail_fast_page = make_page(url=Error(browser_error))
    fail_fast = await build(
        {"url": current_url(_), "title": title(_)},
        PageSummary,
    ).run(fail_fast_page)

    assert fail_fast.is_error()
    assert isinstance(fail_fast.error, BuildFieldError)
    assert fail_fast.error.field == "url"
    assert fail_fast.error.cause is browser_error
    assert fail_fast.error.__cause__ is browser_error
    fail_fast_page.url.assert_awaited_once_with()
    fail_fast_page.title.assert_not_awaited()

    settled_page = make_page(url=Error(browser_error))
    settled = await build_all_settled({"url": current_url(_), "title": title(_)}).run(
        settled_page
    )

    assert settled.is_ok()
    assert list(settled.ok) == ["url", "title"]
    assert settled.ok["url"].is_error()
    assert settled.ok["url"].error is browser_error
    assert settled.ok["title"] == Ok("Example")
    settled_page.url.assert_awaited_once_with()
    settled_page.title.assert_awaited_once_with()

    lossy_page = make_page(url=Error(browser_error))
    lossy = await build_lossy({"url": current_url(_), "title": title(_)}).run(
        lossy_page
    )

    assert lossy == Ok({"title": "Example"})
    lossy_page.url.assert_awaited_once_with()
    lossy_page.title.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_traversal_policies_preserve_order_errors_and_reporting() -> None:
    browser_error = RuntimeError("page crashed")
    first = make_page(url=Ok("https://one.test"))
    failed = make_page(url=Error(browser_error))
    last = make_page(url=Ok("https://three.test"))

    fail_fast = await traverse(current_url(_)).run([first, failed, last])

    assert fail_fast.is_error()
    assert is_indexed_traversal_error(fail_fast.error)
    assert fail_fast.error.index == 1
    assert fail_fast.error.cause is browser_error
    assert fail_fast.error.__cause__ is browser_error
    first.url.assert_awaited_once_with()
    failed.url.assert_awaited_once_with()
    last.url.assert_not_awaited()

    settled = await traverse_all_settled(current_url(_), limit=2).run(
        [first, failed, last]
    )

    assert settled.is_ok()
    assert settled.ok[0] == Ok("https://one.test")
    assert settled.ok[1].is_error()
    assert settled.ok[1].error is browser_error
    assert settled.ok[2] == Ok("https://three.test")

    reports: list[tuple[Page, Exception]] = []

    def report(page: Page, error: Exception) -> None:
        reports.append((page, error))

    lossy = await traverse_lossy(
        current_url(_),
        limit=2,
        on_error=report,
    ).run([first, failed, last])

    assert lossy == Ok(["https://one.test", "https://three.test"])
    assert reports == [(failed, browser_error)]


@pytest.mark.asyncio
async def test_retry_reuses_input_and_capability_and_keeps_final_error() -> None:
    _, capability, environment = driver_environment()
    item = WorkItem("retry-input")
    failures = [
        RuntimeError("first browser failure"),
        RuntimeError("second browser failure"),
        RuntimeError("final browser failure"),
    ]
    seen_inputs: list[WorkItem] = []
    seen_capabilities: list[BrowserDriverCapability] = []
    backoffs: list[tuple[int, Exception]] = []

    @environment_result_operation(DRIVER)
    async def always_fails(
        value: WorkItem,
        seen_capability: BrowserDriverCapability,
    ) -> Result[str, Exception]:
        seen_inputs.append(value)
        seen_capabilities.append(seen_capability)
        return Error(failures[len(seen_inputs) - 1])

    def backoff(attempt: int, error: Exception) -> float:
        backoffs.append((attempt, error))
        return 0.0

    outcome = await retry(
        always_fails,
        attempts=3,
        backoff=backoff,
    ).run(item, environment=environment)

    assert outcome.is_error()
    assert outcome.error is failures[-1]
    assert seen_inputs == [item, item, item]
    assert all(seen is item for seen in seen_inputs)
    assert seen_capabilities == [capability, capability, capability]
    assert all(seen is capability for seen in seen_capabilities)
    assert backoffs == [(1, failures[0]), (2, failures[1])]


@pytest.mark.asyncio
async def test_retry_propagates_cancellation_without_retrying_or_orphaning() -> None:
    _, _, environment = driver_environment()
    item = WorkItem("cancel-retry")
    started = asyncio.Event()
    finalized = asyncio.Event()
    attempts = 0

    @environment_result_operation(DRIVER)
    async def blocks(
        value: WorkItem,
        capability: BrowserDriverCapability,
    ) -> Result[str, Exception]:
        nonlocal attempts
        assert value is item
        assert capability is environment.require(DRIVER)
        attempts += 1
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()
        return Ok("unreachable")

    task = asyncio.create_task(
        retry(blocks, attempts=4).run(item, environment=environment)
    )
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert finalized.is_set()
    assert attempts == 1


@pytest.mark.asyncio
async def test_fanout_parallel_is_bounded_ordered_and_shares_identity() -> None:
    _, capability, environment = driver_environment()
    item = WorkItem("shared")
    release = asyncio.Event()
    probe = ActivityProbe(threshold=2)
    branches = tuple(
        controlled_branch(label, probe, release)
        for label in ("first", "second", "third", "fourth")
    )

    task = asyncio.create_task(
        fanout_parallel(*branches, limit=2).run(
            item,
            environment=environment,
        )
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)

    assert probe.active == 2
    assert probe.max_active == 2
    release.set()
    outcome = await task

    assert outcome == Ok(("first", "second", "third", "fourth"))
    assert probe.max_active == 2
    assert probe.active == 0
    assert len(probe.inputs) == 4
    assert all(seen is item for seen in probe.inputs)
    assert all(seen is capability for seen in probe.capabilities)
    assert sorted(probe.stopped) == sorted(probe.started)


@pytest.mark.asyncio
async def test_fanout_parallel_failure_cancels_and_joins_siblings() -> None:
    _, _, environment = driver_environment()
    item = WorkItem("fail-fast")
    probe = ActivityProbe(threshold=3)
    fail_now = asyncio.Event()
    never_release = asyncio.Event()
    browser_error = RuntimeError("browser disconnected")
    branches = (
        controlled_branch(
            "failed",
            probe,
            fail_now,
            failure=browser_error,
        ),
        controlled_branch("left", probe, never_release),
        controlled_branch("right", probe, never_release),
    )

    task = asyncio.create_task(
        fanout_parallel(*branches).run(item, environment=environment)
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)
    fail_now.set()
    outcome = await task

    assert outcome.is_error()
    assert outcome.error is browser_error
    assert sorted(probe.cancelled) == ["left", "right"]
    assert probe.active == 0
    assert sorted(probe.stopped) == sorted(probe.started)


@pytest.mark.asyncio
async def test_fanout_parallel_external_cancellation_joins_every_branch() -> None:
    _, _, environment = driver_environment()
    item = WorkItem("cancel-fanout")
    probe = ActivityProbe(threshold=3)
    never_release = asyncio.Event()
    branches = tuple(
        controlled_branch(label, probe, never_release)
        for label in ("first", "second", "third")
    )

    task = asyncio.create_task(
        fanout_parallel(*branches).run(item, environment=environment)
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert sorted(probe.cancelled) == ["first", "second", "third"]
    assert probe.active == 0
    assert sorted(probe.stopped) == sorted(probe.started)


@pytest.mark.asyncio
async def test_fanout_all_settled_retains_declaration_order_and_results() -> None:
    _, _, environment = driver_environment()
    item = WorkItem("settled")
    probe = ActivityProbe(threshold=3)
    first_release = asyncio.Event()
    second_release = asyncio.Event()
    third_release = asyncio.Event()
    first_finished = asyncio.Event()
    second_finished = asyncio.Event()
    third_finished = asyncio.Event()
    browser_error = RuntimeError("middle failed")
    branches = (
        controlled_branch("first", probe, first_release, finished=first_finished),
        controlled_branch(
            "second",
            probe,
            second_release,
            failure=browser_error,
            finished=second_finished,
        ),
        controlled_branch("third", probe, third_release, finished=third_finished),
    )

    task = asyncio.create_task(
        fanout_all_settled(*branches).run(item, environment=environment)
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)
    third_release.set()
    await asyncio.wait_for(third_finished.wait(), timeout=2)
    second_release.set()
    await asyncio.wait_for(second_finished.wait(), timeout=2)
    first_release.set()
    await asyncio.wait_for(first_finished.wait(), timeout=2)
    outcome = await task

    assert outcome.is_ok()
    first, second, third = outcome.ok
    assert first == Ok("first")
    assert second.is_error()
    assert second.error is browser_error
    assert third == Ok("third")
    assert probe.stopped == ["third", "second", "first"]
    assert probe.active == 0


@pytest.mark.asyncio
async def test_traverse_parallel_is_bounded_ordered_and_shares_capability() -> None:
    _, capability, environment = driver_environment()
    items = [WorkItem(label) for label in ("one", "two", "three", "four")]
    release = asyncio.Event()
    probe = ActivityProbe(threshold=2)

    @environment_result_operation(DRIVER)
    async def observe(
        item: WorkItem,
        seen_capability: BrowserDriverCapability,
    ) -> Result[str, Exception]:
        probe.enter(item.label, item, seen_capability)
        try:
            await release.wait()
            return Ok(item.label)
        except asyncio.CancelledError:
            probe.cancelled.append(item.label)
            raise
        finally:
            probe.leave(item.label)

    task = asyncio.create_task(
        traverse_parallel(observe, limit=2).run(
            items,
            environment=environment,
        )
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)

    assert probe.active == 2
    assert probe.max_active == 2
    release.set()
    outcome = await task

    assert outcome == Ok(["one", "two", "three", "four"])
    assert probe.max_active == 2
    assert probe.active == 0
    assert len(probe.inputs) == 4
    assert all(seen is expected for seen, expected in zip(probe.inputs, items))
    assert all(seen is capability for seen in probe.capabilities)
    assert sorted(probe.stopped) == sorted(probe.started)


@pytest.mark.asyncio
async def test_traverse_parallel_failure_wraps_cause_and_joins_work() -> None:
    _, _, environment = driver_environment()
    items = [WorkItem(label) for label in ("failed", "blocked", "queued")]
    probe = ActivityProbe(threshold=2)
    fail_now = asyncio.Event()
    never_release = asyncio.Event()
    browser_error = RuntimeError("browser read failed")

    @environment_result_operation(DRIVER)
    async def read(
        item: WorkItem,
        capability: BrowserDriverCapability,
    ) -> Result[str, Exception]:
        probe.enter(item.label, item, capability)
        try:
            if item.label == "failed":
                await fail_now.wait()
                return Error(browser_error)
            await never_release.wait()
            return Ok(item.label)
        except asyncio.CancelledError:
            probe.cancelled.append(item.label)
            raise
        finally:
            probe.leave(item.label)

    task = asyncio.create_task(
        traverse_parallel(read, limit=2).run(
            items,
            environment=environment,
        )
    )
    await asyncio.wait_for(probe.threshold_reached.wait(), timeout=2)
    fail_now.set()
    outcome = await task

    assert outcome.is_error()
    assert is_indexed_traversal_error(outcome.error)
    assert outcome.error.index == 0
    assert outcome.error.cause is browser_error
    assert outcome.error.__cause__ is browser_error
    assert "blocked" in probe.cancelled
    assert probe.max_active <= 2
    assert probe.active == 0
    assert sorted(probe.stopped) == sorted(probe.started)


@pytest.mark.asyncio
async def test_public_context_action_shares_driver_and_immutable_options() -> None:
    driver, capability, environment = driver_environment()
    contexts = [MagicMock(spec=BrowserContext), MagicMock(spec=BrowserContext)]
    options_seen: list[BrowserContextOptions] = []
    active = 0
    max_active = 0
    both_started = asyncio.Event()
    release = asyncio.Event()

    async def new_context(
        options: BrowserContextOptions,
    ) -> Result[BrowserContext, Exception]:
        nonlocal active, max_active
        index = len(options_seen)
        options_seen.append(options)
        active += 1
        max_active = max(max_active, active)
        if active == 2:
            both_started.set()
        try:
            await release.wait()
            return Ok(contexts[index])
        finally:
            active -= 1

    driver.new_context.side_effect = new_context
    configured = BrowserContextOptions(
        viewport=BrowserViewport(width=910, height=620),
        permissions=("clipboard-read",),
    )
    task = asyncio.create_task(
        fanout_parallel(
            create_context(_),
            create_context(_),
            limit=2,
        ).run(configured, environment=environment)
    )
    await asyncio.wait_for(both_started.wait(), timeout=2)

    assert environment.require(DRIVER) is capability
    assert not hasattr(capability, "driver")
    assert active == 2
    release.set()
    outcome = await task

    assert outcome == Ok((contexts[0], contexts[1]))
    assert max_active == 2
    assert active == 0
    assert len(options_seen) == 2
    assert all(options == configured for options in options_seen)
    assert all(options is configured for options in options_seen)
    assert options_seen[0] is options_seen[1]
