# pyright: strict
"""Playwright adapter for Silk's small nominal browser seam."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal, TypeVar, overload
from uuid import uuid4

from fp_ops import Error, Ok, Result
from playwright.async_api import (
    Browser,
)
from playwright.async_api import BrowserContext as PWBrowserContext
from playwright.async_api import ElementHandle as PWElementHandle
from playwright.async_api import Page as PWPage
from playwright.async_api import Playwright as PlaywrightAPIType
from playwright.async_api import (
    ProxySettings,
    ViewportSize,
    async_playwright,
)

from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
    CoordinateType,
    ElementHandle,
    KeyModifier,
    MouseButtonLiteral,
    NavigationWaitLiteral,
    Page,
    WaitStateLiteral,
)
from silk.errors import DragElementMismatchError

_NO_EVALUATION_ARGUMENT = object()
_PlaywrightModifier = Literal["Alt", "Control", "Meta", "Shift"]
T = TypeVar("T")


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


def _capture_base_exception_from_call(action: Callable[[], T]) -> T:
    """Run a synchronous call while wrapping non-Exception exits."""

    with _WrapBaseException():
        return action()
    raise AssertionError("base-exception wrapper exited without a result")


async def _capture_base_exception(awaitable: Awaitable[T]) -> T:
    """Await a call while wrapping non-Exception exits."""

    with _WrapBaseException():
        return await awaitable
    raise AssertionError("base-exception wrapper exited without a result")


def _playwright_modifiers(
    modifiers: tuple[KeyModifier, ...],
) -> list[_PlaywrightModifier]:
    mapping: dict[KeyModifier, _PlaywrightModifier] = {
        KeyModifier.ALT: "Alt",
        KeyModifier.CTRL: "Control",
        KeyModifier.COMMAND: "Meta",
        KeyModifier.SHIFT: "Shift",
    }
    return [mapping[modifier] for modifier in modifiers if modifier in mapping]


@dataclass(frozen=True, slots=True)
class _DriverCleanupReport:
    failures: tuple[Exception, ...] = ()
    interruptions: tuple[BaseException, ...] = ()


class _ContextRegistry:
    """Shared lifecycle state visible to handles, without an umbrella close."""

    __slots__ = (
        "close_attempts",
        "closers",
        "contexts",
        "lock",
        "owner_identity",
    )

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.contexts: dict[str, PlaywrightBrowserContext] = {}
        self.closers: dict[
            str,
            Callable[[], Awaitable[Result[None, Exception]]],
        ] = {}
        self.close_attempts: set[str] = set()
        self.owner_identity = object()


class PlaywrightElementHandle(ElementHandle):
    """Element focus acting directly on private native references."""

    def __init__(
        self,
        native_element: PWElementHandle,
        native_page: PWPage,
        *,
        owner_identity: object,
        page_id: str,
        context_id: str,
        selector: str | None,
    ) -> None:
        self.__native_element = native_element
        self.__native_page = native_page
        self.__owner_identity = owner_identity
        self.__page_id = page_id
        self.__context_id = context_id
        self.__selector = selector

    @property
    def page_id(self) -> str:
        return self.__page_id

    @property
    def context_id(self) -> str:
        return self.__context_id

    @property
    def selector(self) -> str | None:
        return self.__selector

    def _wrap(
        self,
        native_element: PWElementHandle,
        selector: str | None,
    ) -> PlaywrightElementHandle:
        return PlaywrightElementHandle(
            native_element,
            self.__native_page,
            owner_identity=self.__owner_identity,
            page_id=self.__page_id,
            context_id=self.__context_id,
            selector=selector,
        )

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        try:
            native = await self.__native_element.query_selector(selector)
            if native is None:
                return Ok(None)
            return Ok(self._wrap(native, selector))
        except Exception as error:
            return Error(error)

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        try:
            native_elements = await self.__native_element.query_selector_all(selector)
            return Ok([self._wrap(native, selector) for native in native_elements])
        except Exception as error:
            return Error(error)

    async def click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        click_count: int = 1,
        force: bool = False,
    ) -> Result[None, Exception]:
        try:
            await self.__native_element.click(
                button=button,
                click_count=click_count,
                delay=delay_ms,
                timeout=timeout_ms,
                force=force,
                modifiers=_playwright_modifiers(modifiers),
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def double_click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        force: bool = False,
    ) -> Result[None, Exception]:
        try:
            await self.__native_element.dblclick(
                button=button,
                delay=delay_ms,
                timeout=timeout_ms,
                force=force,
                modifiers=_playwright_modifiers(modifiers),
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def fill(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear: bool = False,
    ) -> Result[None, Exception]:
        try:
            if clear:
                await self.__native_element.fill("", timeout=timeout_ms)
            await self.__native_element.fill(text, timeout=timeout_ms)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def type(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        try:
            await self.__native_element.type(
                text,
                delay=delay_ms,
                timeout=timeout_ms,
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def select(
        self,
        *,
        value: str | None = None,
        text: str | None = None,
    ) -> Result[None, Exception]:
        try:
            if value is not None:
                await self.__native_element.select_option(value=value)
            elif text is not None:
                await self.__native_element.select_option(label=text)
            else:
                return Error(ValueError("Either value or text must be provided"))
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def scroll_into_view(self) -> Result[None, Exception]:
        try:
            await self.__native_element.scroll_into_view_if_needed()
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def text(self) -> Result[str, Exception]:
        try:
            value = await self.__native_element.text_content()
            return Ok("" if value is None else value)
        except Exception as error:
            return Error(error)

    async def inner_text(self) -> Result[str, Exception]:
        try:
            return Ok(await self.__native_element.inner_text())
        except Exception as error:
            return Error(error)

    async def html(self, *, outer: bool = True) -> Result[str, Exception]:
        try:
            if outer:
                value: object = await self.__native_element.evaluate(
                    "element => element.outerHTML"
                )
                if not isinstance(value, str):
                    return Error(TypeError("element outer HTML is not text"))
                return Ok(value)
            return Ok(await self.__native_element.inner_html())
        except Exception as error:
            return Error(error)

    async def attribute(
        self,
        name: str,
    ) -> Result[str | None, Exception]:
        try:
            return Ok(await self.__native_element.get_attribute(name))
        except Exception as error:
            return Error(error)

    async def __bounding_box(self) -> Result[dict[str, float], Exception]:
        try:
            box = await self.__native_element.bounding_box()
            if box is None:
                return Error(ValueError("Element has no bounding box"))
            return Ok(
                {
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                }
            )
        except Exception as error:
            return Error(error)

    async def move_pointer_to(
        self,
        *,
        offset: CoordinateType = (0, 0),
        center: bool = True,
        steps: int = 1,
    ) -> Result[None, Exception]:
        if steps < 1:
            return Error(ValueError("mouse_move_to steps must be positive"))
        box_result = await self.__bounding_box()
        if box_result.is_error():
            return Error(box_result.error)
        box = box_result.ok
        x = box["x"] + offset[0]
        y = box["y"] + offset[1]
        if center:
            x += box["width"] / 2
            y += box["height"] / 2
        try:
            await self.__native_page.mouse.move(x, y, steps=steps)
            return Ok(None)
        except Exception as error:
            return Error(error)

    @staticmethod
    def __point(
        box: dict[str, float],
        *,
        move_to_center: bool,
        position_offset: CoordinateType | None,
        endpoint_offset: CoordinateType | None,
    ) -> CoordinateType:
        x = box["x"]
        y = box["y"]
        if move_to_center:
            x += box["width"] / 2
            y += box["height"] / 2
        if position_offset is not None:
            x += position_offset[0]
            y += position_offset[1]
        if endpoint_offset is not None:
            x += endpoint_offset[0]
            y += endpoint_offset[1]
        return int(x), int(y)

    async def __settle_mouse_release(self) -> tuple[BaseException, ...]:
        """Finish one release despite caller cancellation and retain failures."""

        try:
            release_task = _capture_base_exception_from_call(
                lambda: asyncio.create_task(self.__native_page.mouse.up())
            )
        except _CapturedBaseException as captured:
            return (captured.cause,)
        except Exception as error:
            return (error,)

        interruptions: list[BaseException] = []
        while not release_task.done():
            try:
                await _capture_base_exception(asyncio.shield(release_task))
            except _CapturedBaseException as captured:
                if isinstance(captured.cause, asyncio.CancelledError):
                    if not release_task.cancelled():
                        interruptions.append(captured.cause)
                    continue
                break
            except Exception:
                break

        try:
            _capture_base_exception_from_call(release_task.result)
        except _CapturedBaseException as captured:
            interruptions.append(captured.cause)
        except Exception as release_error:
            interruptions.append(release_error)
        return tuple(interruptions)

    @staticmethod
    def __drag_outcome(
        failures: tuple[BaseException, ...],
    ) -> Result[None, Exception]:
        if not failures:
            return Ok(None)
        if len(failures) == 1:
            failure = failures[0]
            if isinstance(failure, Exception):
                return Error(failure)
            raise failure

        ordinary_failures = [
            failure for failure in failures if isinstance(failure, Exception)
        ]
        if len(ordinary_failures) == len(failures):
            return Error(
                ExceptionGroup(
                    "drag failed and mouse release also failed",
                    ordinary_failures,
                )
            )
        raise BaseExceptionGroup(
            "drag was interrupted and mouse release also failed",
            list(failures),
        )

    async def __drag_pointer(
        self,
        source: CoordinateType,
        target: CoordinateType,
        *,
        steps: int,
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.mouse.move(source[0], source[1])
        except Exception as error:
            return Error(error)

        failures: list[BaseException] = []
        try:
            await _capture_base_exception(self.__native_page.mouse.down())
        except _CapturedBaseException as captured:
            failures.append(captured.cause)
        except Exception as primary:
            failures.append(primary)
        else:
            try:
                await _capture_base_exception(
                    self.__native_page.mouse.move(
                        target[0],
                        target[1],
                        steps=steps,
                    )
                )
            except _CapturedBaseException as captured:
                failures.append(captured.cause)
            except Exception as primary:
                failures.append(primary)
        failures.extend(await self.__settle_mouse_release())
        return self.__drag_outcome(tuple(failures))

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
        if steps < 1:
            return Error(ValueError("drag steps must be positive"))
        if not isinstance(target, PlaywrightElementHandle):
            return Error(
                DragElementMismatchError(
                    owner_mismatch=True,
                    source_page_id=self.__page_id,
                    target_page_id=target.page_id,
                )
            )
        owner_mismatch = self.__owner_identity is not target.__owner_identity
        if owner_mismatch or self.__page_id != target.__page_id:
            return Error(
                DragElementMismatchError(
                    owner_mismatch=owner_mismatch,
                    source_page_id=self.__page_id,
                    target_page_id=target.__page_id,
                )
            )
        source_box_result = await self.__bounding_box()
        if source_box_result.is_error():
            return Error(source_box_result.error)
        target_box_result = await target.__bounding_box()
        if target_box_result.is_error():
            return Error(target_box_result.error)

        return await self.__drag_pointer(
            self.__point(
                source_box_result.ok,
                move_to_center=move_to_center,
                position_offset=position_offset,
                endpoint_offset=source_offset,
            ),
            self.__point(
                target_box_result.ok,
                move_to_center=move_to_center,
                position_offset=position_offset,
                endpoint_offset=target_offset,
            ),
            steps=steps,
        )


class PlaywrightPage(Page):
    """Page focus acting directly on a private native page."""

    def __init__(
        self,
        native_page: PWPage,
        *,
        owner_identity: object,
        page_id: str,
        context_id: str,
        lifecycle_lock: asyncio.Lock,
        page_cache: dict[int, PlaywrightPage],
    ) -> None:
        self.__native_page = native_page
        self.__owner_identity = owner_identity
        self.__page_id = page_id
        self.__context_id = context_id
        self.__lifecycle_lock = lifecycle_lock
        self.__page_cache = page_cache
        self.__cache_key = id(native_page)
        self.__closed = False

    @property
    def page_id(self) -> str:
        return self.__page_id

    @property
    def context_id(self) -> str:
        return self.__context_id

    def _wrap_element(
        self,
        native_element: PWElementHandle,
        selector: str | None,
    ) -> PlaywrightElementHandle:
        return PlaywrightElementHandle(
            native_element,
            self.__native_page,
            owner_identity=self.__owner_identity,
            page_id=self.__page_id,
            context_id=self.__context_id,
            selector=selector,
        )

    async def navigate(
        self,
        url: str,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
        referer: str | None = None,
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout_ms,
                referer=referer,
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def url(self) -> Result[str, Exception]:
        try:
            return Ok(self.__native_page.url)
        except Exception as error:
            return Error(error)

    async def title(self) -> Result[str, Exception]:
        try:
            return Ok(await self.__native_page.title())
        except Exception as error:
            return Error(error)

    async def content(self) -> Result[str, Exception]:
        try:
            return Ok(await self.__native_page.content())
        except Exception as error:
            return Error(error)

    async def reload(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.reload(
                wait_until=wait_until,
                timeout=timeout_ms,
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.go_back(
                wait_until=wait_until,
                timeout=timeout_ms,
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.go_forward(
                wait_until=wait_until,
                timeout=timeout_ms,
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def wait_for_navigation(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        """Await Playwright's next main-frame navigation lifecycle."""

        try:
            async with self.__native_page.expect_navigation(
                wait_until=wait_until,
                timeout=timeout_ms,
            ):
                pass
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        try:
            native = await self.__native_page.query_selector(selector)
            if native is None:
                return Ok(None)
            return Ok(self._wrap_element(native, selector))
        except Exception as error:
            return Error(error)

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        try:
            native_elements = await self.__native_page.query_selector_all(selector)
            return Ok(
                [self._wrap_element(native, selector) for native in native_elements]
            )
        except Exception as error:
            return Error(error)

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout_ms: int | None = None,
        state: WaitStateLiteral = "visible",
    ) -> Result[ElementHandle | None, Exception]:
        try:
            native = await self.__native_page.wait_for_selector(
                selector,
                timeout=timeout_ms,
                state=state,
            )
            if native is None:
                return Ok(None)
            return Ok(self._wrap_element(native, selector))
        except Exception as error:
            return Error(error)

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
        try:
            value: object
            if argument is _NO_EVALUATION_ARGUMENT:
                value = await self.__native_page.evaluate(script)
            else:
                value = await self.__native_page.evaluate(script, argument)
            return Ok(value)
        except Exception as error:
            return Error(error)

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]: ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]: ...

    async def screenshot(
        self,
        path: Path | None = None,
    ) -> Result[Path | bytes, Exception]:
        try:
            if path is not None:
                await self.__native_page.screenshot(path=str(path))
                return Ok(path)
            return Ok(await self.__native_page.screenshot())
        except Exception as error:
            return Error(error)

    async def mouse_move(
        self,
        x: float,
        y: float,
        *,
        steps: int = 1,
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.mouse.move(x, y, steps=steps)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def mouse_down(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.mouse.down(button=button)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def mouse_up(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.mouse.up(button=button)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def key_press(
        self,
        key: str,
        *,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.keyboard.press(key, delay=delay_ms)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def key_down(self, key: str) -> Result[None, Exception]:
        try:
            await self.__native_page.keyboard.down(key)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def key_up(self, key: str) -> Result[None, Exception]:
        try:
            await self.__native_page.keyboard.up(key)
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def scroll(
        self,
        *,
        x: int = 0,
        y: int = 0,
    ) -> Result[None, Exception]:
        try:
            await self.__native_page.evaluate(
                "position => window.scrollTo(position.x, position.y)",
                {"x": x, "y": y},
            )
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def close(self) -> Result[None, Exception]:
        async with self.__lifecycle_lock:
            return await self._close_locked()

    async def _close_locked(self) -> Result[None, Exception]:
        if self.__closed:
            return Ok(None)
        try:
            await self.__native_page.close()
        except Exception as error:
            return Error(error)
        self.__closed = True
        self.__page_cache.pop(self.__cache_key, None)
        return Ok(None)


class PlaywrightBrowserContext(BrowserContext):
    """Context focus with private native ownership and page cache."""

    def __init__(
        self,
        native_context: PWBrowserContext,
        *,
        context_id: str,
        registry: _ContextRegistry,
        owner_identity: object,
    ) -> None:
        self.__native_context = native_context
        self.__context_id = context_id
        self.__registry = registry
        self.__owner_identity = owner_identity
        self.__pages: dict[int, PlaywrightPage] = {}
        self.__closed = False
        self.__registry.closers[self.__context_id] = self.__close_locked

    @property
    def context_id(self) -> str:
        return self.__context_id

    def _page_for(self, native_page: PWPage) -> PlaywrightPage:
        cache_key = id(native_page)
        cached = self.__pages.get(cache_key)
        if cached is not None:
            return cached
        page = PlaywrightPage(
            native_page,
            owner_identity=self.__owner_identity,
            page_id=str(uuid4()),
            context_id=self.__context_id,
            lifecycle_lock=self.__registry.lock,
            page_cache=self.__pages,
        )
        self.__pages[cache_key] = page
        return page

    def __invalidate(self) -> None:
        self.__closed = True
        self.__pages.clear()
        self.__registry.contexts.pop(self.__context_id, None)
        self.__registry.closers.pop(self.__context_id, None)
        self.__registry.close_attempts.discard(self.__context_id)

    async def new_page(self) -> Result[Page, Exception]:
        async with self.__registry.lock:
            if self.__closed or self.__context_id not in self.__registry.contexts:
                return Error(ValueError("Browser context is closed"))
            try:
                native_page = await self.__native_context.new_page()
                return Ok(self._page_for(native_page))
            except Exception as error:
                return Error(error)

    async def pages(self) -> Result[list[Page], Exception]:
        async with self.__registry.lock:
            if self.__closed or self.__context_id not in self.__registry.contexts:
                return Error(ValueError("Browser context is closed"))
            try:
                native_pages = self.__native_context.pages
                live_keys = {id(native) for native in native_pages}
                for cache_key in tuple(self.__pages):
                    if cache_key not in live_keys:
                        self.__pages.pop(cache_key, None)
                return Ok([self._page_for(native) for native in native_pages])
            except Exception as error:
                return Error(error)

    async def close(self) -> Result[None, Exception]:
        async with self.__registry.lock:
            return await self.__close_locked()

    async def __close_locked(self) -> Result[None, Exception]:
        if self.__closed:
            return Ok(None)
        self.__registry.close_attempts.add(self.__context_id)
        try:
            await self.__native_context.close()
        except Exception as error:
            return Error(error)
        self.__invalidate()
        return Ok(None)


class _PlaywrightDriver:
    """Private Playwright lifecycle root owned by one ``BrowserSession``."""

    def __init__(self) -> None:
        self._playwright: PlaywrightAPIType | None = None
        self._browser: Browser | None = None
        self._manager: AbstractAsyncContextManager[PlaywrightAPIType] | None = None
        self._registry = _ContextRegistry()
        self._launch_allowed = True

    @property
    def has_pending_cleanup(self) -> bool:
        return (
            self._playwright is not None
            or self._browser is not None
            or self._manager is not None
            or bool(self._registry.contexts)
            or bool(self._registry.closers)
            or bool(self._registry.close_attempts)
        )

    async def launch(
        self,
        options: BrowserOptions | None = None,
    ) -> Result[None, Exception]:
        async with self._registry.lock:
            return await self._launch_locked(options)

    async def _launch_locked(
        self,
        options: BrowserOptions | None = None,
    ) -> Result[None, Exception]:
        if not self._launch_allowed or self.has_pending_cleanup:
            return Error(
                RuntimeError(
                    "Playwright driver is already launched or must be closed "
                    "successfully before relaunch"
                )
            )
        self._launch_allowed = False
        configured = options if options is not None else BrowserOptions()
        try:
            manager = async_playwright()
            self._manager = manager
            playwright = await manager.__aenter__()
            self._playwright = playwright
            proxy: ProxySettings | None = None
            if configured.proxy is not None:
                proxy = {"server": configured.proxy.server}
            self._browser = await playwright.chromium.launch(
                headless=configured.headless,
                timeout=configured.timeout,
                args=configured.args,
                proxy=proxy,
            )
            self._registry.owner_identity = object()
            return Ok(None)
        except Exception as error:
            return Error(error)

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        async with self._registry.lock:
            return await self._new_context_locked(options)

    async def _new_context_locked(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        browser = self._browser
        if browser is None:
            return Error(ValueError("Browser not launched"))
        configured = options if options is not None else BrowserContextOptions()
        try:
            viewport: ViewportSize | None = None
            if configured.viewport is not None:
                viewport = {
                    "width": configured.viewport.width,
                    "height": configured.viewport.height,
                }
            headers = (
                dict(configured.extra_http_headers)
                if configured.extra_http_headers is not None
                else None
            )
            proxy: ProxySettings | None = None
            if configured.proxy is not None:
                proxy = {"server": configured.proxy.server}
                if configured.proxy.bypass is not None:
                    proxy["bypass"] = configured.proxy.bypass
                if configured.proxy.username is not None:
                    proxy["username"] = configured.proxy.username
                if configured.proxy.password is not None:
                    proxy["password"] = configured.proxy.password
            native_context = await browser.new_context(
                viewport=viewport,
                permissions=configured.permissions,
                user_agent=configured.user_agent,
                extra_http_headers=headers,
                proxy=proxy,
                locale=configured.locale,
                timezone_id=configured.timezone_id,
                ignore_https_errors=configured.ignore_https_errors,
                java_script_enabled=configured.java_script_enabled,
            )
            if configured.timeout is not None:
                native_context.set_default_timeout(configured.timeout)
            if configured.navigation_timeout is not None:
                native_context.set_default_navigation_timeout(
                    configured.navigation_timeout
                )
            context_id = str(uuid4())
            context = PlaywrightBrowserContext(
                native_context,
                context_id=context_id,
                registry=self._registry,
                owner_identity=self._registry.owner_identity,
            )
            self._registry.contexts[context_id] = context
            return Ok(context)
        except Exception as error:
            return Error(error)

    async def _close_all_settled(self) -> _DriverCleanupReport:
        async with self._registry.lock:
            return await self._close_all_settled_locked()

    async def _close_all_settled_locked(self) -> _DriverCleanupReport:
        if self.has_pending_cleanup:
            self._launch_allowed = False
        failures: list[Exception] = []
        interruptions: list[BaseException] = []
        previously_attempted = frozenset(self._registry.close_attempts)

        for context_id, closer in tuple(self._registry.closers.items()):
            if context_id in previously_attempted:
                continue
            try:
                result = await _capture_base_exception(closer())
            except _CapturedBaseException as captured:
                interruptions.append(captured.cause)
            except Exception as interruption:
                interruptions.append(interruption)
            else:
                if result.is_error():
                    failures.append(result.error)

        browser = self._browser
        if browser is not None:
            try:
                await _capture_base_exception(browser.close())
            except _CapturedBaseException as captured:
                interruptions.append(captured.cause)
            except Exception as failure:
                failures.append(failure)
            else:
                self._browser = None
                self._registry.contexts.clear()
                self._registry.closers.clear()
                self._registry.close_attempts.clear()

        manager = self._manager
        if manager is not None:
            try:
                await _capture_base_exception(manager.__aexit__(None, None, None))
            except _CapturedBaseException as captured:
                interruptions.append(captured.cause)
            except Exception as failure:
                failures.append(failure)
            else:
                self._manager = None
                self._playwright = None

        report = _DriverCleanupReport(
            failures=tuple(failures),
            interruptions=tuple(interruptions),
        )
        if (
            not report.failures
            and not report.interruptions
            and not self.has_pending_cleanup
        ):
            self._launch_allowed = True
        return report

    @staticmethod
    async def _join_close_task(
        cleanup_task: asyncio.Task[_DriverCleanupReport],
    ) -> tuple[_DriverCleanupReport, tuple[asyncio.CancelledError, ...]]:
        cancellations: list[asyncio.CancelledError] = []
        while not cleanup_task.done():
            try:
                report = await asyncio.shield(cleanup_task)
                return report, tuple(cancellations)
            except asyncio.CancelledError as cancellation:
                cancellations.append(cancellation)
        return cleanup_task.result(), tuple(cancellations)

    async def close(self) -> Result[None, Exception]:
        cleanup_task = asyncio.create_task(
            self._close_all_settled(),
            name="silk-playwright-driver-close",
        )
        report, cancellations = await self._join_close_task(cleanup_task)
        interruptions = (*cancellations, *report.interruptions)
        if interruptions:
            combined = [*interruptions, *report.failures]
            if len(combined) == 1:
                raise combined[0]
            raise BaseExceptionGroup(
                "Playwright driver cleanup was interrupted and failed",
                combined,
            )
        if not report.failures:
            return Ok(None)
        if len(report.failures) == 1:
            return Error(report.failures[0])
        return Error(
            ExceptionGroup(
                "Playwright driver cleanup failed",
                list(report.failures),
            )
        )


__all__: list[str] = []
assert _PlaywrightDriver.__name__ not in __all__
