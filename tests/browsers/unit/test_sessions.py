from __future__ import annotations

import asyncio
import inspect
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock

import pytest
from fp_ops import Environment, EnvironmentError, Error, Ok, operation

import silk.browsers.drivers.playwright as playwright_adapter
from silk.browsers import (
    BROWSER_OPTIONS,
    BROWSER_SESSION,
    DRIVER,
    BrowserContext,
    BrowserDriverCapability,
    BrowserOptions,
    BrowserOptionsCapability,
    BrowserSession,
    BrowserSessionCleanupError,
    BrowserSessionInfo,
    Page,
)
from silk.browsers.capabilities import BrowserSessionNotStartedError
from silk.browsers.models import BrowserContextOptions


class _DriverDouble:
    """Test-local structural spec for the monkeypatched lifecycle root."""

    has_pending_cleanup = True

    async def launch(self, options=None):
        raise NotImplementedError

    async def new_context(self, options=None):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError


@pytest.fixture
def browser_harness(monkeypatch: pytest.MonkeyPatch):
    page = MagicMock(spec=Page)
    page.page_id = "initial-page"
    page.close = AsyncMock(return_value=Ok(None))

    context = MagicMock(spec=BrowserContext)
    context.context_id = "initial-context"
    context.new_page = AsyncMock(return_value=Ok(page))
    context.close = AsyncMock(return_value=Ok(None))

    driver = MagicMock(spec=_DriverDouble)
    driver.launch = AsyncMock(return_value=Ok(None))
    driver.new_context = AsyncMock(return_value=Ok(context))
    driver.close = AsyncMock(return_value=Ok(None))

    driver_factory = MagicMock(return_value=driver)
    monkeypatch.setattr(playwright_adapter, "_PlaywrightDriver", driver_factory)
    return driver_factory, driver, context, page


def test_public_session_constructor_owns_adapter_selection() -> None:
    signature = inspect.signature(BrowserSession)
    session = BrowserSession()

    assert tuple(signature.parameters) == ("options", "context_options")
    assert (
        signature.parameters["context_options"].kind is inspect.Parameter.KEYWORD_ONLY
    )
    assert not hasattr(BrowserSession, "_for_testing")
    assert not hasattr(session, "driver")
    assert not hasattr(session, "_driver")
    assert not hasattr(session, "_driver_factory")
    assert not hasattr(session, "_resources")
    with pytest.raises(TypeError, match="driver_class"):
        BrowserSession(driver_class=MagicMock())


@pytest.mark.asyncio
async def test_started_session_exposes_explicit_focus_and_stable_environment(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    options = BrowserOptions(headless=True)
    session = BrowserSession(options=options)

    started = await session.start()

    assert started is session
    assert session.page is page
    assert session.context is context
    assert set(session.environment) == {DRIVER, BROWSER_SESSION, BROWSER_OPTIONS}
    capability = session.environment.require(DRIVER)
    assert not hasattr(capability, "driver")
    assert not hasattr(capability, "close")
    assert session.environment.require(BROWSER_SESSION) == BrowserSessionInfo(
        session_id=session.session_id
    )
    driver.launch.assert_awaited_once_with(options)
    driver.new_context.assert_awaited_once_with(None)

    with pytest.raises(FrozenInstanceError):
        options.headless = False
    assert session.environment.require(BROWSER_OPTIONS).options is options

    @operation
    def same_page(value: Page) -> Page:
        return value

    result = await same_page.run(session.page, environment=session.environment)
    assert result.ok is page

    await session.close()


@pytest.mark.asyncio
async def test_captured_driver_capability_rejects_use_after_session_close(
    browser_harness,
):
    driver_factory, driver, _, _ = browser_harness
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)

    await session.close()
    outcome = await capability.new_context(BrowserContextOptions())

    assert outcome.is_error()
    assert isinstance(outcome.error, BrowserSessionNotStartedError)
    assert outcome.error.session_id == session.session_id
    assert "not started" in str(outcome.error)
    assert session.is_started is False
    assert not hasattr(capability, "driver")
    assert not hasattr(capability, "close")
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.page
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.context
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.environment
    driver.new_context.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_captured_capability_cannot_rejoin_a_restarted_session(
    browser_harness,
):
    driver_factory, driver, context, _ = browser_harness
    session = await BrowserSession().start()
    stale_capability = session.environment.require(DRIVER)

    await session.close()
    await session.start()
    current_capability = session.environment.require(DRIVER)

    stale_outcome = await stale_capability.new_context(BrowserContextOptions())
    current_outcome = await current_capability.new_context(BrowserContextOptions())

    assert stale_outcome.is_error()
    assert isinstance(stale_outcome.error, BrowserSessionNotStartedError)
    assert current_outcome == Ok(context)
    assert stale_capability is not current_capability
    assert session.is_started is True
    assert driver.new_context.await_count == 3

    await session.close()


@pytest.mark.asyncio
async def test_capability_context_creation_finishes_before_queued_cleanup(
    browser_harness,
):
    driver_factory, driver, initial_context, page = browser_harness
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)
    creation_started = asyncio.Event()
    allow_creation = asyncio.Event()
    extra_context = MagicMock(spec=BrowserContext)
    options = BrowserContextOptions()

    async def blocking_new_context(received_options):
        assert received_options is options
        creation_started.set()
        await allow_creation.wait()
        return Ok(extra_context)

    driver.new_context.side_effect = blocking_new_context
    creation_task = asyncio.create_task(capability.new_context(options))
    await creation_started.wait()
    cleanup_task = asyncio.create_task(session.close())
    try:
        await asyncio.sleep(0)
        assert not cleanup_task.done()
    finally:
        allow_creation.set()

    creation_outcome, cleanup_outcome = await asyncio.gather(
        creation_task,
        cleanup_task,
    )
    assert creation_outcome == Ok(extra_context)
    assert cleanup_outcome is None
    assert session.is_started is False
    page.close.assert_awaited_once_with()
    initial_context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_capability_context_creation_queued_behind_cleanup_is_rejected(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)
    page_close_started = asyncio.Event()
    allow_page_close = asyncio.Event()

    async def blocking_page_close():
        page_close_started.set()
        await allow_page_close.wait()
        return Ok(None)

    page.close.side_effect = blocking_page_close
    cleanup_task = asyncio.create_task(session.close())
    await page_close_started.wait()
    creation_task = asyncio.create_task(capability.new_context(BrowserContextOptions()))
    try:
        await asyncio.sleep(0)
        assert not creation_task.done()
    finally:
        allow_page_close.set()

    cleanup_outcome, creation_outcome = await asyncio.gather(
        cleanup_task,
        creation_task,
    )
    assert cleanup_outcome is None
    assert creation_outcome.is_error()
    assert isinstance(
        creation_outcome.error,
        BrowserSessionNotStartedError,
    )
    assert creation_outcome.error.session_id == session.session_id
    assert session.is_started is False
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()
    driver.new_context.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_capability_context_creation_preserves_cause_and_can_retry(
    browser_harness,
):
    driver_factory, driver, _, _ = browser_harness
    session = await BrowserSession().start()
    capability = session.environment.require(DRIVER)
    cause = RuntimeError("context creation failed")
    recovered = MagicMock(spec=BrowserContext)
    driver.new_context.side_effect = [Error(cause), Ok(recovered)]

    failed = await capability.new_context(BrowserContextOptions())
    retried = await capability.new_context(BrowserContextOptions())

    assert failed.is_error()
    assert failed.error is cause
    assert retried == Ok(recovered)
    assert session.is_started is True

    await session.close()
    first_stale = await capability.new_context(BrowserContextOptions())
    second_stale = await capability.new_context(BrowserContextOptions())
    assert first_stale.is_error()
    assert second_stale.is_error()
    assert isinstance(first_stale.error, BrowserSessionNotStartedError)
    assert isinstance(second_stale.error, BrowserSessionNotStartedError)


def test_session_focus_is_unavailable_outside_started_lifetime(browser_harness):
    driver_factory, _, _, _ = browser_harness
    session = BrowserSession()

    with pytest.raises(RuntimeError, match="not started"):
        _ = session.page
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.context
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.environment


@pytest.mark.asyncio
async def test_start_is_fail_fast_and_rolls_back_acquired_resources(browser_harness):
    driver_factory, driver, context, _ = browser_harness
    page_error = RuntimeError("page failed")
    context.new_page.return_value = Error(page_error)
    session = BrowserSession()

    with pytest.raises(RuntimeError) as raised:
        await session.start()

    assert raised.value is page_error
    context.close.assert_awaited_once()
    driver.close.assert_awaited_once()
    assert session.is_started is False


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["launch", "context", "page"])
async def test_start_cancellation_cleans_every_acquired_resource(
    browser_harness,
    stage,
):
    driver_factory, driver, context, _ = browser_harness
    cancellation = asyncio.CancelledError(f"cancelled during {stage}")
    if stage == "launch":
        driver.launch.side_effect = cancellation
    elif stage == "context":
        driver.new_context.side_effect = cancellation
    else:
        context.new_page.side_effect = cancellation
    session = BrowserSession()

    with pytest.raises(asyncio.CancelledError) as raised:
        await session.start()

    assert raised.value is cancellation
    driver.close.assert_awaited_once()
    if stage == "page":
        context.close.assert_awaited_once()
    else:
        context.close.assert_not_awaited()
    assert session.is_started is False


@pytest.mark.asyncio
async def test_start_cancellation_groups_cleanup_failure_and_retains_both_causes(
    browser_harness,
):
    driver_factory, driver, context, _ = browser_harness
    cancellation = asyncio.CancelledError("page acquisition cancelled")
    cleanup_cause = RuntimeError("driver close failed")
    context.new_page.side_effect = cancellation
    driver.close.return_value = Error(cleanup_cause)
    session = BrowserSession()

    with pytest.raises(BaseExceptionGroup) as raised:
        await session.start()

    assert raised.value.exceptions[0] is cancellation
    cleanup_error = raised.value.exceptions[1]
    assert isinstance(cleanup_error, BrowserSessionCleanupError)
    assert cleanup_error.resource == "driver"
    assert cleanup_error.cause is cleanup_cause
    context.close.assert_awaited_once()
    driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_propagates_non_exception_base_exception_after_cleanup(
    browser_harness,
):
    class FatalStartup(BaseException):
        pass

    driver_factory, driver, context, _ = browser_harness
    fatal = FatalStartup("fatal page failure")
    context.new_page.side_effect = fatal
    session = BrowserSession()

    with pytest.raises(FatalStartup) as raised:
        await session.start()

    assert raised.value is fatal
    context.close.assert_awaited_once()
    driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_ordinary_startup_and_cleanup_failures_are_grouped(browser_harness):
    driver_factory, driver, _, _ = browser_harness
    startup_cause = RuntimeError("launch failed")
    cleanup_cause = RuntimeError("driver close failed")
    driver.launch.return_value = Error(startup_cause)
    driver.close.return_value = Error(cleanup_cause)
    session = BrowserSession()

    with pytest.raises(ExceptionGroup) as raised:
        await session.start()

    assert raised.value.exceptions[0] is startup_cause
    cleanup_error = raised.value.exceptions[1]
    assert isinstance(cleanup_error, BrowserSessionCleanupError)
    assert cleanup_error.cause is cleanup_cause


@pytest.mark.asyncio
async def test_startup_rollback_retains_failed_driver_until_public_retry(
    browser_harness,
):
    driver_factory, driver, _, _ = browser_harness
    startup_cause = RuntimeError("launch failed")
    cleanup_cause = RuntimeError("driver close failed")
    driver.launch.return_value = Error(startup_cause)
    driver.close.side_effect = [Error(cleanup_cause), Ok(None)]
    session = BrowserSession()

    with pytest.raises(ExceptionGroup) as raised:
        await session.start()

    assert raised.value.exceptions[0] is startup_cause
    cleanup_error = raised.value.exceptions[1]
    assert isinstance(cleanup_error, BrowserSessionCleanupError)
    assert cleanup_error.cause is cleanup_cause
    with pytest.raises(RuntimeError, match="resources pending cleanup"):
        await session.start()
    assert driver_factory.call_count == 1

    assert await session.close_all_settled() == ()
    assert driver.close.await_count == 2


@pytest.mark.asyncio
async def test_all_settled_cleanup_attempts_every_resource_and_retains_causes(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    causes = {
        "page": RuntimeError("page close failed"),
        "context": RuntimeError("context close failed"),
        "driver": RuntimeError("driver close failed"),
    }
    page.close.return_value = Error(causes["page"])
    context.close.side_effect = causes["context"]
    driver.close.return_value = Error(causes["driver"])

    failures = await session.close_all_settled()

    assert tuple(failure.resource for failure in failures) == (
        "page",
        "context",
        "driver",
    )
    assert tuple(failure.cause for failure in failures) == tuple(causes.values())
    assert all(failure.__cause__ is failure.cause for failure in failures)
    page.close.assert_awaited_once()
    context.close.assert_awaited_once()
    driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_fail_fast_cleanup_stops_at_first_failure(browser_harness):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    cause = RuntimeError("page close failed")
    page.close.return_value = Error(cause)

    with pytest.raises(BrowserSessionCleanupError) as raised:
        await session.close_fail_fast()

    assert raised.value.resource == "page"
    assert raised.value.cause is cause
    assert raised.value.__cause__ is cause
    context.close.assert_not_awaited()
    driver.close.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_cancelled_fail_fast_stops_after_the_in_flight_resource(
    browser_harness,
    cleanup_fails,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    page_close_started = asyncio.Event()
    allow_page_close = asyncio.Event()
    cleanup_cause = RuntimeError("page close failed")

    async def blocking_page_close():
        page_close_started.set()
        await allow_page_close.wait()
        if cleanup_fails:
            return Error(cleanup_cause)
        return Ok(None)

    page.close.side_effect = blocking_page_close
    cleanup_task = asyncio.create_task(session.close_fail_fast())
    await page_close_started.wait()
    cleanup_task.cancel("cancelled during fail-fast cleanup")
    await asyncio.sleep(0)
    allow_page_close.set()

    if cleanup_fails:
        with pytest.raises(BaseExceptionGroup) as raised:
            await cleanup_task
        cancellation, cleanup_error = raised.value.exceptions
        assert isinstance(cancellation, asyncio.CancelledError)
        assert cancellation.args == ("cancelled during fail-fast cleanup",)
        assert isinstance(cleanup_error, BrowserSessionCleanupError)
        assert cleanup_error.resource == "page"
        assert cleanup_error.cause is cleanup_cause
    else:
        with pytest.raises(asyncio.CancelledError) as raised:
            await cleanup_task
        assert raised.value.args == ("cancelled during fail-fast cleanup",)

    context.close.assert_not_awaited()
    driver.close.assert_not_awaited()
    assert session.is_started is False
    assert not any(
        task.get_name().startswith("silk-browser-session-cleanup")
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    )

    page.close.side_effect = None
    page.close.return_value = Ok(None)
    assert await session.close_all_settled() == ()
    assert page.close.await_count == (2 if cleanup_fails else 1)
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_concurrent_mixed_cleanup_is_serialized_on_success(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    page_close_started = asyncio.Event()
    allow_page_close = asyncio.Event()

    async def blocking_page_close():
        page_close_started.set()
        await allow_page_close.wait()
        return Ok(None)

    page.close.side_effect = blocking_page_close
    all_settled = asyncio.create_task(session.close_all_settled())
    await page_close_started.wait()
    ordinary = asyncio.create_task(session.close())
    fail_fast = asyncio.create_task(session.close_fail_fast())
    await asyncio.sleep(0)
    allow_page_close.set()

    assert await all_settled == ()
    assert await ordinary is None
    assert await fail_fast is None
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()
    assert not any(
        task.get_name().startswith("silk-browser-session-cleanup")
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        ("close", None),
        ("close_all_settled", ()),
        ("close_fail_fast", None),
    ],
)
async def test_cleanup_queued_during_start_closes_the_completed_session(
    browser_harness,
    policy,
    expected,
):
    driver_factory, driver, context, page = browser_harness
    launch_started = asyncio.Event()
    allow_launch = asyncio.Event()

    async def blocking_launch(_options):
        launch_started.set()
        await allow_launch.wait()
        return Ok(None)

    driver.launch.side_effect = blocking_launch
    session = BrowserSession()
    start_task = asyncio.create_task(session.start())
    await launch_started.wait()

    async def run_cleanup():
        if policy == "close":
            return await session.close()
        if policy == "close_all_settled":
            return await session.close_all_settled()
        return await session.close_fail_fast()

    cleanup_task = asyncio.create_task(run_cleanup())
    try:
        await asyncio.sleep(0)
        assert not cleanup_task.done()
    finally:
        allow_launch.set()

    assert await start_task is session
    assert await cleanup_task == expected
    assert session.is_started is False
    with pytest.raises(RuntimeError, match="not started"):
        _ = session.page
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_cancelled_cleanup_queued_during_start_is_joined_without_orphans(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    launch_started = asyncio.Event()
    allow_launch = asyncio.Event()

    async def blocking_launch(_options):
        launch_started.set()
        await allow_launch.wait()
        return Ok(None)

    driver.launch.side_effect = blocking_launch
    session = BrowserSession()
    start_task = asyncio.create_task(session.start())
    await launch_started.wait()
    cleanup_task = asyncio.create_task(session.close())
    await asyncio.sleep(0)

    cleanup_task.cancel("cancelled while queued behind startup")
    await asyncio.sleep(0)
    allow_launch.set()

    assert await start_task is session
    with pytest.raises(asyncio.CancelledError) as raised:
        await cleanup_task
    assert raised.value.args == ("cancelled while queued behind startup",)
    assert session.is_started is False
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()
    assert not any(
        task.get_name().startswith("silk-browser-session-cleanup")
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    )


@pytest.mark.asyncio
async def test_concurrent_cleanup_failure_is_retried_serially(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    driver_close_started = asyncio.Event()
    allow_driver_close = asyncio.Event()
    first_cause = RuntimeError("umbrella driver close failed")
    active_closes = 0
    maximum_active_closes = 0
    close_calls = 0

    async def fail_then_succeed():
        nonlocal active_closes, close_calls, maximum_active_closes
        close_calls += 1
        active_closes += 1
        maximum_active_closes = max(maximum_active_closes, active_closes)
        try:
            if close_calls == 1:
                driver_close_started.set()
                await allow_driver_close.wait()
                return Error(first_cause)
            return Ok(None)
        finally:
            active_closes -= 1

    driver.close.side_effect = fail_then_succeed
    first = asyncio.create_task(session.close_all_settled())
    await driver_close_started.wait()
    retry = asyncio.create_task(session.close())
    await asyncio.sleep(0)
    allow_driver_close.set()

    first_failures = await first
    assert tuple(failure.resource for failure in first_failures) == ("driver",)
    assert first_failures[0].cause is first_cause
    assert await retry is None
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    assert driver.close.await_count == 2
    assert maximum_active_closes == 1


@pytest.mark.asyncio
async def test_cancelling_one_concurrent_cleanup_waiter_does_not_duplicate_close(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    page_close_started = asyncio.Event()
    allow_page_close = asyncio.Event()

    async def blocking_page_close():
        page_close_started.set()
        await allow_page_close.wait()
        return Ok(None)

    page.close.side_effect = blocking_page_close
    owner = asyncio.create_task(session.close_all_settled())
    await page_close_started.wait()
    waiter = asyncio.create_task(session.close_fail_fast())
    await asyncio.sleep(0)
    waiter.cancel("cancelled while queued behind cleanup")
    await asyncio.sleep(0)
    allow_page_close.set()

    assert await owner == ()
    with pytest.raises(asyncio.CancelledError) as raised:
        await waiter
    assert raised.value.args == ("cancelled while queued behind cleanup",)
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    driver.close.assert_awaited_once_with()
    assert not any(
        task.get_name().startswith("silk-browser-session-cleanup")
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy",
    ["close", "close_all_settled", "close_fail_fast"],
)
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_public_cleanup_cancellation_is_joined_and_never_wrapped(
    browser_harness,
    policy,
    cleanup_fails,
):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    close_started = asyncio.Event()
    allow_page_close = asyncio.Event()
    cleanup_cause = RuntimeError("page close failed")
    propagated = []

    async def blocking_page_close():
        close_started.set()
        await allow_page_close.wait()
        if cleanup_fails:
            return Error(cleanup_cause)
        return Ok(None)

    page.close.side_effect = blocking_page_close

    async def run_cleanup():
        try:
            if policy == "close":
                await session.close()
            elif policy == "close_all_settled":
                await session.close_all_settled()
            else:
                await session.close_fail_fast()
        except BaseException as error:
            propagated.append(error)
            raise

    task = asyncio.create_task(run_cleanup())
    await close_started.wait()
    task.cancel(f"cancelled during {policy}")
    await asyncio.sleep(0)
    allow_page_close.set()

    if cleanup_fails:
        with pytest.raises(BaseExceptionGroup) as raised:
            await task
        cancellation, cleanup_error = raised.value.exceptions
        assert propagated == [raised.value]
        assert isinstance(cancellation, asyncio.CancelledError)
        assert cancellation.args == (f"cancelled during {policy}",)
        assert isinstance(cleanup_error, BrowserSessionCleanupError)
        assert cleanup_error.resource == "page"
        assert cleanup_error.cause is cleanup_cause
        assert cleanup_error.__cause__ is cleanup_cause
    else:
        with pytest.raises(asyncio.CancelledError) as raised:
            await task
        assert propagated == [raised.value]
        assert raised.value.args == (f"cancelled during {policy}",)

    page.close.assert_awaited_once()
    if policy == "close_fail_fast":
        context.close.assert_not_awaited()
        driver.close.assert_not_awaited()
        page.close.side_effect = None
        page.close.return_value = Ok(None)
        assert await session.close_all_settled() == ()
        assert page.close.await_count == (2 if cleanup_fails else 1)
        context.close.assert_awaited_once_with()
        driver.close.assert_awaited_once_with()
    else:
        context.close.assert_awaited_once()
        driver.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy",
    ["close", "close_all_settled", "close_fail_fast"],
)
@pytest.mark.parametrize("ordinary_failure", [False, True])
async def test_public_cleanup_propagates_other_base_exceptions(
    browser_harness,
    policy,
    ordinary_failure,
):
    class FatalCleanup(BaseException):
        pass

    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    interruption = FatalCleanup("fatal page close")
    ordinary_cause = RuntimeError("context close failed")
    page.close.side_effect = interruption
    if ordinary_failure:
        context.close.return_value = Error(ordinary_cause)

    async def run_cleanup():
        if policy == "close":
            await session.close()
        elif policy == "close_all_settled":
            await session.close_all_settled()
        else:
            await session.close_fail_fast()

    if policy == "close_fail_fast":
        with pytest.raises(FatalCleanup) as raised:
            await run_cleanup()
        assert raised.value is interruption
        page.close.assert_awaited_once_with()
        context.close.assert_not_awaited()
        driver.close.assert_not_awaited()

        page.close.side_effect = None
        page.close.return_value = Ok(None)
        retry_failures = await session.close_all_settled()
        if ordinary_failure:
            assert len(retry_failures) == 1
            assert retry_failures[0].resource == "context"
            assert retry_failures[0].cause is ordinary_cause
        else:
            assert retry_failures == ()
        context.close.assert_awaited_once_with()
        driver.close.assert_awaited_once_with()
    else:
        if ordinary_failure:
            with pytest.raises(BaseExceptionGroup) as raised:
                await run_cleanup()
            propagated_interruption, cleanup_error = raised.value.exceptions
            assert propagated_interruption is interruption
            assert isinstance(cleanup_error, BrowserSessionCleanupError)
            assert cleanup_error.resource == "context"
            assert cleanup_error.cause is ordinary_cause
        else:
            with pytest.raises(FatalCleanup) as raised:
                await run_cleanup()
            assert raised.value is interruption

        page.close.assert_awaited_once()
        context.close.assert_awaited_once()
        driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_reports_aggregate_after_attempting_all_cleanup(browser_harness):
    driver_factory, driver, context, page = browser_harness
    session = await BrowserSession().start()
    page.close.return_value = Error(RuntimeError("page close failed"))
    driver.close.return_value = Error(RuntimeError("driver close failed"))

    with pytest.raises(ExceptionGroup) as raised:
        await session.close()

    assert [failure.resource for failure in raised.value.exceptions] == [
        "page",
        "driver",
    ]
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager_groups_body_and_cleanup_failures(browser_harness):
    driver_factory, _, _, page = browser_harness
    body_cause = RuntimeError("pipeline failed")
    cleanup_cause = RuntimeError("page close failed")
    page.close.return_value = Error(cleanup_cause)

    with pytest.raises(ExceptionGroup) as raised:
        async with BrowserSession():
            raise body_cause

    assert raised.value.exceptions[0] is body_cause
    cleanup_error = raised.value.exceptions[1]
    assert isinstance(cleanup_error, BrowserSessionCleanupError)
    assert cleanup_error.cause is cleanup_cause


@pytest.mark.asyncio
async def test_context_manager_retains_failed_driver_until_public_retry(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    cleanup_cause = RuntimeError("driver close failed")
    driver.close.side_effect = [Error(cleanup_cause), Ok(None)]
    session = BrowserSession()

    with pytest.raises(BrowserSessionCleanupError) as raised:
        async with session:
            pass

    assert raised.value.resource == "driver"
    assert raised.value.cause is cleanup_cause
    assert await session.close_all_settled() == ()
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    assert driver.close.await_count == 2


@pytest.mark.asyncio
async def test_fail_fast_driver_interruption_retains_only_driver_for_retry(
    browser_harness,
):
    driver_factory, driver, context, page = browser_harness
    interruption = asyncio.CancelledError("native driver close interrupted")
    driver.close.side_effect = [interruption, Ok(None)]
    session = await BrowserSession().start()

    with pytest.raises(asyncio.CancelledError) as raised:
        await session.close_fail_fast()

    assert raised.value is interruption
    assert await session.close_all_settled() == ()
    page.close.assert_awaited_once_with()
    context.close.assert_awaited_once_with()
    assert driver.close.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_cancellation_during_context_cleanup_is_joined_and_propagated(
    browser_harness,
    cleanup_fails,
):
    driver_factory, driver, context, page = browser_harness
    close_started = asyncio.Event()
    allow_page_close = asyncio.Event()
    cleanup_cause = RuntimeError("page close failed")

    async def blocking_page_close():
        close_started.set()
        await allow_page_close.wait()
        if cleanup_fails:
            return Error(cleanup_cause)
        return Ok(None)

    page.close.side_effect = blocking_page_close

    async def use_session():
        async with BrowserSession():
            pass

    task = asyncio.create_task(use_session())
    await close_started.wait()
    task.cancel("cancelled during browser cleanup")
    await asyncio.sleep(0)
    allow_page_close.set()

    if cleanup_fails:
        with pytest.raises(BaseExceptionGroup) as raised:
            await task
        cancellation, cleanup_error = raised.value.exceptions
        assert isinstance(cancellation, asyncio.CancelledError)
        assert cancellation.args == ("cancelled during browser cleanup",)
        assert isinstance(cleanup_error, BrowserSessionCleanupError)
        assert cleanup_error.resource == "page"
        assert cleanup_error.cause is cleanup_cause
    else:
        with pytest.raises(asyncio.CancelledError) as raised:
            await task
        assert raised.value.args == ("cancelled during browser cleanup",)

    page.close.assert_awaited_once()
    context.close.assert_awaited_once()
    driver.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_can_start_close_and_restart(browser_harness):
    driver_factory, driver, context, page = browser_harness
    session = BrowserSession()

    first_started = await session.start()
    first_environment = session.environment
    await session.close()
    second_started = await session.start()

    assert first_started is second_started is session
    assert session.environment is not first_environment
    assert session.page is page
    assert session.context is context
    assert session.environment.require(BROWSER_SESSION).session_id == session.session_id
    assert driver_factory.call_count == 2
    assert driver.close.await_count == 1

    await session.close()
    assert driver.close.await_count == 2


def test_capability_values_validate_at_environment_construction(browser_harness):
    _, driver, _, _ = browser_harness
    capability = BrowserDriverCapability(driver.new_context)
    info = BrowserSessionInfo("session-1")

    environment = (
        Environment()
        .with_value(DRIVER, capability)
        .with_value(BROWSER_SESSION, info)
        .with_value(
            BROWSER_OPTIONS,
            BrowserOptionsCapability(BrowserOptions()),
        )
    )

    assert environment.require(DRIVER) is capability
    assert environment.require(BROWSER_SESSION) is info
    with pytest.raises(EnvironmentError, match="requires BrowserSessionInfo"):
        Environment().with_value(BROWSER_SESSION, object())
    with pytest.raises(FrozenInstanceError):
        info.session_id = "changed"


def test_browser_options_capability_holds_the_exact_immutable_value():
    source = BrowserOptions(
        headless=True,
        args=("--first",),
    )
    capability = BrowserOptionsCapability(source)

    assert capability.options is source
    assert capability.options.args == ("--first",)
    assert copy(capability) is capability
    assert deepcopy(capability) is capability
    with pytest.raises(FrozenInstanceError):
        capability.options.headless = False
