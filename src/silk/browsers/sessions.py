"""Browser lifecycle management with explicit pipeline focus and capabilities."""

# pyright: strict

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from importlib import import_module
from types import TracebackType
from typing import (
    Callable,
    Coroutine,
    Literal,
    Never,
    Protocol,
    TypeVar,
    runtime_checkable,
)
from uuid import uuid4
from weakref import ref

from fp_ops import Environment, Error, Result

from silk.browsers.capabilities import (
    BROWSER_OPTIONS,
    BROWSER_SESSION,
    DRIVER,
    BrowserDriverCapability,
    BrowserOptionsCapability,
    BrowserSessionInfo,
    BrowserSessionNotStartedError,
    NewBrowserContext,
)
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
    Page,
)

CleanupResource = Literal["page", "context", "driver"]
T = TypeVar("T")


class BrowserSessionCleanupError(Exception):
    """One browser resource failed to close."""

    def __init__(self, resource: CleanupResource, cause: Exception) -> None:
        self.resource = resource
        self.cause = cause
        self.__cause__ = cause
        super().__init__(resource, cause)

    def __str__(self) -> str:
        return f"failed to close browser {self.resource}: {self.cause}"


class _CapturedBaseException(Exception):
    """Temporarily carry a non-Exception interruption through ordinary flow."""

    def __init__(self, cause: BaseException) -> None:
        self.cause = cause
        super().__init__(cause)


class _WrapBaseException:
    """Convert only non-Exception exits into an inspectable interruption."""

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_value is None or isinstance(exc_value, Exception):
            return False
        raise _CapturedBaseException(exc_value) from exc_value


async def _capture_base_exception(awaitable: Awaitable[T]) -> T:
    """Re-raise non-Exception failures in an inspectable ordinary wrapper."""

    with _WrapBaseException():
        return await awaitable
    raise AssertionError("base-exception wrapper exited without a result")


class _Closable(Protocol):
    async def close(self) -> Result[None, Exception]: ...


@runtime_checkable
class _SessionDriver(_Closable, Protocol):
    """Private structural lifecycle seam owned exclusively by a session."""

    @property
    def has_pending_cleanup(self) -> bool: ...

    async def launch(
        self,
        options: BrowserOptions | None = None,
    ) -> Result[None, Exception]: ...

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]: ...


@runtime_checkable
class _CleanupOwner(Protocol):
    @property
    def has_pending_cleanup(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class _CleanupReport:
    failures: tuple[BrowserSessionCleanupError, ...] = ()
    interruptions: tuple[BaseException, ...] = ()
    attempted: tuple[CleanupResource, ...] = ()


def _unwrap(result: Result[T, Exception]) -> T:
    if result.is_error():
        raise result.error
    return result.ok


class BrowserSession:
    """Own one driver, initial browser context, and initial page.

    A started session exposes the page as ordinary pipeline input and exposes a
    read-only fp-ops environment containing only stable capabilities::

        async with BrowserSession() as session:
            result = await pipeline.run(
                session.page,
                environment=session.environment,
            )

    ``close`` attempts every acquired resource and then reports any failures.
    ``close_fail_fast`` is available when stopping at the first cleanup failure
    is explicitly required. ``close_all_settled`` never raises ordinary cleanup
    failures and returns each one with its original cause. Startup and cleanup
    are serialized; each later caller observes the ownership state left by the
    completed lifecycle call ahead of it.
    """

    def __init__(
        self,
        options: BrowserOptions | None = None,
        *,
        context_options: BrowserContextOptions | None = None,
    ) -> None:
        self.__options = options if options is not None else BrowserOptions()
        self.__context_options = context_options
        self.__session_id = str(uuid4())
        self.__driver: _SessionDriver | None = None
        self.__context: BrowserContext | None = None
        self.__page: Page | None = None
        self.__environment: Environment | None = None
        self.__active_capability_token: object | None = None
        self.__started = False
        self.__lifecycle_lock = asyncio.Lock()

    @property
    def session_id(self) -> str:
        """Return this session's stable identity."""

        return self.__session_id

    @property
    def is_started(self) -> bool:
        """Report whether the initial page and environment are ready."""

        return self.__started

    @property
    def page(self) -> Page:
        """Return the explicit initial page of a started session."""

        if not self.__started or self.__page is None:
            raise RuntimeError("browser session is not started")
        return self.__page

    @property
    def context(self) -> BrowserContext:
        """Return the explicitly owned initial browser context."""

        if not self.__started or self.__context is None:
            raise RuntimeError("browser session is not started")
        return self.__context

    @property
    def environment(self) -> Environment:
        """Return the stable capabilities of a started session."""

        if not self.__started or self.__environment is None:
            raise RuntimeError("browser session is not started")
        return self.__environment

    async def start(self) -> BrowserSession:
        """Acquire the driver, initial context, and initial page fail-fast."""

        async with self.__lifecycle_lock:
            return await self._start_locked()

    async def _start_locked(self) -> BrowserSession:
        if self.__started:
            raise RuntimeError("browser session is already started")
        if self._has_acquired_resources():
            raise RuntimeError("browser session has resources pending cleanup")

        try:
            adapter_module = import_module("silk.browsers.drivers.playwright")
            implementation: object = getattr(
                adapter_module,
                "_PlaywrightDriver",
                None,
            )
            if not callable(implementation):
                raise RuntimeError("browser session implementation is unavailable")
            candidate: object = implementation()
            if not isinstance(candidate, _SessionDriver):
                raise TypeError("browser session implementation has an invalid shape")
            driver = candidate
            self.__driver = driver
            _unwrap(await driver.launch(self.__options))

            context = _unwrap(await driver.new_context(self.__context_options))
            self.__context = context

            page = _unwrap(await context.new_page())
            self.__page = page

            capability_token = object()
            environment = (
                Environment()
                .with_value(
                    DRIVER,
                    BrowserDriverCapability(
                        self._new_context_factory(capability_token)
                    ),
                )
                .with_value(
                    BROWSER_SESSION,
                    BrowserSessionInfo(session_id=self.session_id),
                )
                .with_value(
                    BROWSER_OPTIONS,
                    BrowserOptionsCapability(self.__options),
                )
            )
            self.__active_capability_token = capability_token
            self.__environment = environment
            self.__started = True
            return self
        except BaseException as startup_error:
            report = await self._run_cleanup_body_joined(
                self._cleanup_all_settled_locked
            )
            if report.failures or report.interruptions:
                errors = [
                    startup_error,
                    *report.interruptions,
                    *report.failures,
                ]
                if isinstance(startup_error, Exception) and not report.interruptions:
                    raise ExceptionGroup(
                        "browser session startup and cleanup failed",
                        [startup_error, *report.failures],
                    )
                raise BaseExceptionGroup(
                    "browser session startup and cleanup failed",
                    errors,
                )
            raise

    def _new_context_factory(self, token: object) -> NewBrowserContext:
        """Build the weak callback retained by one environment capability."""

        session_ref = ref(self)
        session_id = self.session_id

        async def new_context(
            options: BrowserContextOptions | None,
        ) -> Result[BrowserContext, Exception]:
            session = session_ref()
            if session is None:
                return Error(BrowserSessionNotStartedError(session_id))
            return await session._new_context_from_capability(token, options)

        return new_context

    async def _new_context_from_capability(
        self,
        token: object,
        options: BrowserContextOptions | None,
    ) -> Result[BrowserContext, Exception]:
        async with self.__lifecycle_lock:
            driver = self.__driver
            if (
                not self.__started
                or token is not self.__active_capability_token
                or driver is None
            ):
                return Error(BrowserSessionNotStartedError(self.session_id))
            return await driver.new_context(options)

    async def close(self) -> None:
        """Close all resources, then raise retained cleanup failure(s)."""

        failures = await self.close_all_settled()
        if failures:
            self._raise_cleanup_failures(failures)

    async def close_fail_fast(self) -> None:
        """Close resources in dependency order, stopping on the first failure."""

        stop_requested = asyncio.Event()

        async def cleanup() -> _CleanupReport:
            return await self._cleanup_fail_fast(stop_requested)

        report = await self._run_cleanup_joined(
            cleanup,
            stop_on_cancel=stop_requested,
        )
        if report.interruptions:
            self._raise_cleanup_interruptions(report)
        if report.failures:
            failure = report.failures[0]
            raise failure from failure.cause

    async def close_all_settled(self) -> tuple[BrowserSessionCleanupError, ...]:
        """Attempt every acquired close and return all ordinary failures."""

        report = await self._run_cleanup_joined(self._cleanup_all_settled)
        if report.interruptions:
            self._raise_cleanup_interruptions(report)
        return report.failures

    async def _cleanup_fail_fast(
        self,
        stop_requested: asyncio.Event,
    ) -> _CleanupReport:
        async with self.__lifecycle_lock:
            return await self._cleanup_fail_fast_locked(stop_requested)

    async def _cleanup_fail_fast_locked(
        self,
        stop_requested: asyncio.Event,
    ) -> _CleanupReport:
        self.__started = False
        self.__environment = None
        self.__active_capability_token = None
        failures: list[BrowserSessionCleanupError] = []
        interruptions: list[BaseException] = []
        attempted: list[CleanupResource] = []

        for resource, target in self.__resources():
            if stop_requested.is_set():
                break
            if target is None:
                continue
            attempted.append(resource)
            try:
                failure = await _capture_base_exception(
                    self._settle_close(resource, target)
                )
            except _CapturedBaseException as captured:
                interruptions.append(captured.cause)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                break
            except Exception as interruption:
                interruptions.append(interruption)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                break
            if failure is not None:
                failures.append(failure)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                break
            self._clear_closed_resource(resource)

        return _CleanupReport(
            failures=tuple(failures),
            interruptions=tuple(interruptions),
            attempted=tuple(attempted),
        )

    async def _cleanup_all_settled(
        self,
        skip: frozenset[CleanupResource] = frozenset(),
    ) -> _CleanupReport:
        async with self.__lifecycle_lock:
            return await self._cleanup_all_settled_locked(skip)

    async def _cleanup_all_settled_locked(
        self,
        skip: frozenset[CleanupResource] = frozenset(),
    ) -> _CleanupReport:
        self.__started = False
        self.__environment = None
        self.__active_capability_token = None
        failures: list[BrowserSessionCleanupError] = []
        interruptions: list[BaseException] = []
        attempted: list[CleanupResource] = []

        for resource, target in self.__resources():
            if target is None or resource in skip:
                continue
            attempted.append(resource)
            try:
                failure = await _capture_base_exception(
                    self._settle_close(resource, target)
                )
            except _CapturedBaseException as captured:
                interruptions.append(captured.cause)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                continue
            except Exception as interruption:
                interruptions.append(interruption)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                continue
            if failure is not None:
                failures.append(failure)
                if resource == "driver":
                    self._reconcile_failed_driver_close(target)
                continue
            self._clear_closed_resource(resource)

        return _CleanupReport(
            failures=tuple(failures),
            interruptions=tuple(interruptions),
            attempted=tuple(attempted),
        )

    def __resources(
        self,
    ) -> tuple[tuple[CleanupResource, _Closable | None], ...]:
        return (
            ("page", self.__page),
            ("context", self.__context),
            ("driver", self.__driver),
        )

    def _clear_resource(self, resource: CleanupResource) -> None:
        if resource == "page":
            self.__page = None
        elif resource == "context":
            self.__context = None
        else:
            self.__driver = None

    def _clear_closed_resource(self, resource: CleanupResource) -> None:
        if resource == "driver":
            self._clear_resource_tree()
            return
        self._clear_resource(resource)

    def _clear_resource_tree(self) -> None:
        self.__page = None
        self.__context = None
        self.__driver = None

    def _reconcile_failed_driver_close(self, target: _Closable) -> None:
        if isinstance(target, _CleanupOwner) and not target.has_pending_cleanup:
            self._clear_resource_tree()
            return

        # The driver is the ownership root. Once its umbrella close has failed
        # or been interrupted, retry only that root: child failures have already
        # been reported and adapter registries decide what the umbrella retries.
        self.__page = None
        self.__context = None

    def _has_acquired_resources(self) -> bool:
        return any(
            resource is not None
            for resource in (self.__page, self.__context, self.__driver)
        )

    @staticmethod
    async def _settle_close(
        resource: CleanupResource,
        target: _Closable,
    ) -> BrowserSessionCleanupError | None:
        try:
            result = await target.close()
            if result.is_error():
                return BrowserSessionCleanupError(resource, result.error)
        except Exception as cause:
            return BrowserSessionCleanupError(resource, cause)
        return None

    @staticmethod
    async def _join_cleanup_task(
        cleanup_task: asyncio.Task[_CleanupReport],
        stop_on_cancel: asyncio.Event | None = None,
    ) -> tuple[_CleanupReport, tuple[asyncio.CancelledError, ...]]:
        cancellations: list[asyncio.CancelledError] = []
        while not cleanup_task.done():
            try:
                report = await asyncio.shield(cleanup_task)
                return report, tuple(cancellations)
            except asyncio.CancelledError as cancellation:
                cancellations.append(cancellation)
                if stop_on_cancel is not None:
                    stop_on_cancel.set()
        return cleanup_task.result(), tuple(cancellations)

    async def _run_cleanup_body_joined(
        self,
        cleanup: Callable[[], Coroutine[object, object, _CleanupReport]],
        *,
        stop_on_cancel: asyncio.Event | None = None,
    ) -> _CleanupReport:
        cleanup_task = asyncio.create_task(
            cleanup(),
            name="silk-browser-session-cleanup",
        )
        report, cancellations = await self._join_cleanup_task(
            cleanup_task,
            stop_on_cancel,
        )
        report = _CleanupReport(
            failures=report.failures,
            interruptions=(*cancellations, *report.interruptions),
            attempted=report.attempted,
        )

        return report

    async def _run_cleanup_joined(
        self,
        cleanup: Callable[[], Coroutine[object, object, _CleanupReport]],
        *,
        stop_on_cancel: asyncio.Event | None = None,
    ) -> _CleanupReport:
        return await self._run_cleanup_body_joined(
            cleanup,
            stop_on_cancel=stop_on_cancel,
        )

    @staticmethod
    def _raise_cleanup_interruptions(report: _CleanupReport) -> Never:
        if len(report.interruptions) == 1 and not report.failures:
            raise report.interruptions[0]
        raise BaseExceptionGroup(
            "browser session cleanup was interrupted and failed",
            [*report.interruptions, *report.failures],
        )

    @staticmethod
    def _raise_cleanup_failures(
        failures: tuple[BrowserSessionCleanupError, ...],
    ) -> Never:
        if len(failures) == 1:
            failure = failures[0]
            raise failure from failure.cause
        raise ExceptionGroup("browser session cleanup failed", list(failures))

    async def __aenter__(self) -> BrowserSession:
        return await self.start()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        report = await self._run_cleanup_joined(self._cleanup_all_settled)
        cleanup_errors = [*report.interruptions, *report.failures]
        if not cleanup_errors:
            return
        if exc_value is None:
            if report.interruptions:
                self._raise_cleanup_interruptions(report)
            self._raise_cleanup_failures(report.failures)
        raise BaseExceptionGroup(
            "browser session body and cleanup failed",
            [exc_value, *cleanup_errors],
        )


__all__ = ["BrowserSession", "BrowserSessionCleanupError", "CleanupResource"]
