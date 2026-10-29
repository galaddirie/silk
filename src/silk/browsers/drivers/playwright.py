# pyright: strict
"""Playwright implementation of Silk's browser interfaces."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast, overload
from uuid import uuid4

from fp_ops import Error, Ok, Result
from playwright.async_api import (
    Browser as PWBrowser,
    BrowserContext as PWBrowserContext,
    ElementHandle as PWElementHandle,
    FloatRect,
    Frame as PWFrame,
    Page as PWPage,
    Playwright,
    ProxySettings,
    Route,
    ViewportSize,
    async_playwright,
)

from silk.browsers.drivers.support import attempt as _native_attempt
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserDriver,
    BrowserOptions,
    BrowserProxy,
    CoordinateType,
    ElementHandle,
    Frame,
    KeyModifier,
    LaunchedBrowser,
    MouseButtonLiteral,
    NavigationWaitLiteral,
    Page,
    RequestBlocking,
    WaitStateLiteral,
)
from silk.errors import (
    BrowserError,
    BrowserTimeoutError,
    DragElementMismatchError,
    NavigationError,
    TargetClosedError,
)

T = TypeVar("T")

BrowserTypeLiteral = Literal["chromium", "firefox", "webkit"]

_NO_EVALUATION_ARGUMENT = object()
_MODIFIERS: dict[KeyModifier, Literal["Alt", "Control", "Meta", "Shift"]] = {
    KeyModifier.ALT: "Alt",
    KeyModifier.CTRL: "Control",
    KeyModifier.COMMAND: "Meta",
    KeyModifier.SHIFT: "Shift",
}


_NATIVE_PACKAGES = ("playwright", "patchright")


def _native_class_names(error: Exception) -> set[str] | None:
    """Class names in the MRO if ``error`` comes from Playwright or a fork."""

    module = type(error).__module__
    if not module.startswith(_NATIVE_PACKAGES):
        return None
    return {cls.__name__ for cls in type(error).__mro__}


def translate_error(
    error: Exception, *, navigation_url: str | None = None
) -> Exception:
    """Map a native Playwright/Patchright error onto Silk's ``BrowserError`` types.

    Matching is by exception class (forks ship their own classes with the same
    names), never by message. The native error is kept as ``__cause__``; errors
    from anywhere else are returned unchanged.
    """

    names = _native_class_names(error)
    if names is None:
        return error
    translated: BrowserError
    if "TimeoutError" in names:
        translated = BrowserTimeoutError(str(error))
    elif "TargetClosedError" in names:
        translated = TargetClosedError(str(error))
    elif navigation_url is not None:
        translated = NavigationError(str(error), url=navigation_url)
    else:
        translated = BrowserError(str(error))
    translated.__cause__ = error
    return translated


async def _attempt(
    awaitable: Awaitable[T],
    *,
    navigation_url: str | None = None,
) -> Result[T, Exception]:
    outcome = await _native_attempt(awaitable)
    if outcome.is_error():
        return Error(translate_error(outcome.error, navigation_url=navigation_url))
    return outcome


class _PlaywrightStarter(Protocol):
    async def start(self) -> Playwright: ...


def _modifiers(
    modifiers: tuple[KeyModifier, ...],
) -> list[Literal["Alt", "Control", "Meta", "Shift"]]:
    return [_MODIFIERS[modifier] for modifier in modifiers if modifier in _MODIFIERS]


def _proxy_settings(proxy: BrowserProxy | None) -> ProxySettings | None:
    if proxy is None:
        return None
    settings: ProxySettings = {"server": proxy.server}
    if proxy.bypass is not None:
        settings["bypass"] = proxy.bypass
    if proxy.username is not None:
        settings["username"] = proxy.username
    if proxy.password is not None:
        settings["password"] = proxy.password
    return settings


def _point(
    box: FloatRect,
    *,
    center: bool,
    offsets: tuple[CoordinateType | None, ...],
) -> CoordinateType:
    x = box["x"]
    y = box["y"]
    if center:
        x += box["width"] / 2
        y += box["height"] / 2
    for offset in offsets:
        if offset is not None:
            x += offset[0]
            y += offset[1]
    return int(x), int(y)


class PlaywrightElementHandle(ElementHandle):
    def __init__(
        self,
        native: PWElementHandle,
        page: PlaywrightPage,
        selector: str | None,
    ) -> None:
        self._native = native
        self._page = page
        self._selector = selector

    @property
    def native(self) -> PWElementHandle:
        """The underlying Playwright element handle (an escape hatch)."""

        return self._native

    @property
    def page(self) -> PlaywrightPage:
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

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        found = await _attempt(self._native.query_selector(selector))
        return found.map(lambda native: self._page.wrap_element(native, selector))

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        found = await _attempt(self._native.query_selector_all(selector))
        return found.map(
            lambda natives: [
                PlaywrightElementHandle(native, self._page, selector)
                for native in natives
            ]
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
        return await _attempt(
            self._native.click(
                button=button,
                click_count=click_count,
                delay=delay_ms,
                timeout=timeout_ms,
                force=force,
                modifiers=_modifiers(modifiers),
                position=(
                    None if position is None else {"x": position[0], "y": position[1]}
                ),
            )
        )

    async def content_frame(self) -> Result[Frame | None, Exception]:
        found = await _attempt(self._native.content_frame())
        return found.map(
            lambda native: (
                None if native is None else PlaywrightFrame(native, self._page)
            )
        )

    async def double_click(
        self,
        *,
        timeout_ms: int | None = None,
        button: MouseButtonLiteral = "left",
        modifiers: tuple[KeyModifier, ...] = (),
        delay_ms: int | None = None,
        force: bool = False,
    ) -> Result[None, Exception]:
        return await _attempt(
            self._native.dblclick(
                button=button,
                delay=delay_ms,
                timeout=timeout_ms,
                force=force,
                modifiers=_modifiers(modifiers),
            )
        )

    async def fill(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        clear: bool = False,
    ) -> Result[None, Exception]:
        if clear:
            cleared = await _attempt(self._native.fill("", timeout=timeout_ms))
            if cleared.is_error():
                return cleared
        return await _attempt(self._native.fill(text, timeout=timeout_ms))

    async def type(
        self,
        text: str,
        *,
        timeout_ms: int | None = None,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        return await _attempt(
            self._native.type(text, delay=delay_ms, timeout=timeout_ms)
        )

    async def select(
        self,
        *,
        value: str | None = None,
        text: str | None = None,
    ) -> Result[None, Exception]:
        if value is not None:
            selected = await _attempt(self._native.select_option(value=value))
        elif text is not None:
            selected = await _attempt(self._native.select_option(label=text))
        else:
            return Error(ValueError("Either value or text must be provided"))
        return selected.map(lambda _values: None)

    async def scroll_into_view(self) -> Result[None, Exception]:
        return await _attempt(self._native.scroll_into_view_if_needed())

    async def text(self) -> Result[str, Exception]:
        content = await _attempt(self._native.text_content())
        return content.map(lambda value: "" if value is None else value)

    async def inner_text(self) -> Result[str, Exception]:
        return await _attempt(self._native.inner_text())

    async def html(self, *, outer: bool = True) -> Result[str, Exception]:
        if not outer:
            return await _attempt(self._native.inner_html())
        evaluated = await _attempt(
            self._native.evaluate("element => element.outerHTML")
        )
        if evaluated.is_error():
            return Error(evaluated.error)
        value: object = evaluated.ok
        if not isinstance(value, str):
            return Error(TypeError("element outer HTML is not text"))
        return Ok(value)

    async def attribute(self, name: str) -> Result[str | None, Exception]:
        return await _attempt(self._native.get_attribute(name))

    async def _bounding_box(self) -> Result[FloatRect, Exception]:
        box = await _attempt(self._native.bounding_box())
        if box.is_error():
            return Error(box.error)
        if box.ok is None:
            return Error(ValueError("Element has no bounding box"))
        return Ok(box.ok)

    async def move_pointer_to(
        self,
        *,
        offset: CoordinateType = (0, 0),
        center: bool = True,
        steps: int = 1,
    ) -> Result[None, Exception]:
        if steps < 1:
            return Error(ValueError("mouse_move_to steps must be positive"))
        box = await self._bounding_box()
        if box.is_error():
            return Error(box.error)
        x, y = _point(box.ok, center=center, offsets=(offset,))
        return await _attempt(self._page.native.mouse.move(x, y, steps=steps))

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
        if not isinstance(target, PlaywrightElementHandle) or (
            target._page is not self._page
        ):
            return Error(DragElementMismatchError(self.page_id, target.page_id))

        source_box = await self._bounding_box()
        if source_box.is_error():
            return Error(source_box.error)
        target_box = await target._bounding_box()
        if target_box.is_error():
            return Error(target_box.error)

        source = _point(
            source_box.ok,
            center=move_to_center,
            offsets=(position_offset, source_offset),
        )
        destination = _point(
            target_box.ok,
            center=move_to_center,
            offsets=(position_offset, target_offset),
        )
        return await _attempt(self._drag(source, destination, steps=steps))

    async def _drag(
        self,
        source: CoordinateType,
        destination: CoordinateType,
        *,
        steps: int,
    ) -> None:
        mouse = self._page.native.mouse
        await mouse.move(source[0], source[1])
        try:
            await mouse.down()
            await mouse.move(destination[0], destination[1], steps=steps)
        finally:
            await mouse.up()


class PlaywrightFrame(Frame):
    """A frame inside a page; elements found here belong to that page."""

    def __init__(self, native: PWFrame, page: PlaywrightPage) -> None:
        self._native = native
        self._page = page

    @property
    def native(self) -> PWFrame:
        return self._native

    @property
    def page(self) -> PlaywrightPage:
        return self._page

    async def url(self) -> Result[str, Exception]:
        return Ok(self._native.url)

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        found = await _attempt(self._native.query_selector(selector))
        return found.map(lambda native: self._page.wrap_element(native, selector))

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        found = await _attempt(self._native.query_selector_all(selector))
        return found.map(
            lambda natives: [
                PlaywrightElementHandle(native, self._page, selector)
                for native in natives
            ]
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout_ms: int | None = None,
        state: WaitStateLiteral = "visible",
    ) -> Result[ElementHandle | None, Exception]:
        found = await _attempt(
            self._native.wait_for_selector(selector, timeout=timeout_ms, state=state)
        )
        return found.map(lambda native: self._page.wrap_element(native, selector))

    async def evaluate(self, script: str) -> Result[object, Exception]:
        return await _attempt(self._native.evaluate(script))


class PlaywrightPage(Page):
    def __init__(self, native: PWPage, context: PlaywrightBrowserContext) -> None:
        self.native = native
        self._context = context
        self._page_id = str(uuid4())

    @property
    def page_id(self) -> str:
        return self._page_id

    @property
    def context_id(self) -> str:
        return self._context.context_id

    def wrap_element(
        self,
        native: PWElementHandle | None,
        selector: str | None,
    ) -> PlaywrightElementHandle | None:
        if native is None:
            return None
        return PlaywrightElementHandle(native, self, selector)

    async def navigate(
        self,
        url: str,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
        referer: str | None = None,
    ) -> Result[None, Exception]:
        navigated = await _attempt(
            self.native.goto(
                url,
                wait_until=wait_until,
                timeout=timeout_ms,
                referer=referer,
            ),
            navigation_url=url,
        )
        return navigated.map(lambda _response: None)

    async def url(self) -> Result[str, Exception]:
        return Ok(self.native.url)

    async def base_url(self) -> Result[str, Exception]:
        found = await _attempt(self.native.evaluate("document.baseURI"))
        return found.map(
            lambda value: value if isinstance(value, str) else self.native.url
        )

    async def title(self) -> Result[str, Exception]:
        return await _attempt(self.native.title())

    async def content(self) -> Result[str, Exception]:
        return await _attempt(self.native.content())

    async def reload(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        reloaded = await _attempt(
            self.native.reload(wait_until=wait_until, timeout=timeout_ms),
            navigation_url=self.native.url,
        )
        return reloaded.map(lambda _response: None)

    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        moved = await _attempt(
            self.native.go_back(wait_until=wait_until, timeout=timeout_ms),
            navigation_url=self.native.url,
        )
        return moved.map(lambda _response: None)

    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        moved = await _attempt(
            self.native.go_forward(wait_until=wait_until, timeout=timeout_ms),
            navigation_url=self.native.url,
        )
        return moved.map(lambda _response: None)

    async def wait_for_navigation(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        async def wait() -> None:
            async with self.native.expect_navigation(
                wait_until=wait_until,
                timeout=timeout_ms,
            ):
                pass

        return await _attempt(wait(), navigation_url=self.native.url)

    async def query_selector(
        self,
        selector: str,
    ) -> Result[ElementHandle | None, Exception]:
        found = await _attempt(self.native.query_selector(selector))
        return found.map(lambda native: self.wrap_element(native, selector))

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[ElementHandle], Exception]:
        found = await _attempt(self.native.query_selector_all(selector))
        return found.map(
            lambda natives: [
                PlaywrightElementHandle(native, self, selector) for native in natives
            ]
        )

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout_ms: int | None = None,
        state: WaitStateLiteral = "visible",
    ) -> Result[ElementHandle | None, Exception]:
        found = await _attempt(
            self.native.wait_for_selector(selector, timeout=timeout_ms, state=state)
        )
        return found.map(lambda native: self.wrap_element(native, selector))

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
        if argument is _NO_EVALUATION_ARGUMENT:
            return await _attempt(self.native.evaluate(script))
        return await _attempt(self.native.evaluate(script, argument))

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]: ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]: ...

    async def screenshot(
        self,
        path: Path | None = None,
    ) -> Result[Path | bytes, Exception]:
        if path is None:
            return await _attempt(self.native.screenshot())
        saved = await _attempt(self.native.screenshot(path=str(path)))
        return saved.map(lambda _bytes: path)

    async def mouse_move(
        self,
        x: float,
        y: float,
        *,
        steps: int = 1,
    ) -> Result[None, Exception]:
        return await _attempt(self.native.mouse.move(x, y, steps=steps))

    async def mouse_down(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        return await _attempt(self.native.mouse.down(button=button))

    async def mouse_up(
        self,
        *,
        button: MouseButtonLiteral = "left",
    ) -> Result[None, Exception]:
        return await _attempt(self.native.mouse.up(button=button))

    async def key_press(
        self,
        key: str,
        *,
        delay_ms: int | None = None,
    ) -> Result[None, Exception]:
        return await _attempt(self.native.keyboard.press(key, delay=delay_ms))

    async def key_down(self, key: str) -> Result[None, Exception]:
        return await _attempt(self.native.keyboard.down(key))

    async def key_up(self, key: str) -> Result[None, Exception]:
        return await _attempt(self.native.keyboard.up(key))

    async def scroll(self, *, x: int = 0, y: int = 0) -> Result[None, Exception]:
        scrolled = await _attempt(
            self.native.evaluate(
                "position => window.scrollTo(position.x, position.y)",
                {"x": x, "y": y},
            )
        )
        return scrolled.map(lambda _value: None)

    async def close(self) -> Result[None, Exception]:
        closed = await _attempt(self.native.close())
        if closed.is_ok():
            self._context.forget(self.native)
        return closed


class PlaywrightBrowserContext(BrowserContext):
    def __init__(self, native: PWBrowserContext) -> None:
        self._native = native
        self._context_id = str(uuid4())
        # One wrapper per native page so a page keeps a stable ``page_id``.
        self._pages: dict[int, PlaywrightPage] = {}

    @property
    def native(self) -> PWBrowserContext:
        """The underlying Playwright context (an escape hatch)."""

        return self._native

    @property
    def context_id(self) -> str:
        return self._context_id

    def _wrap(self, native: PWPage) -> PlaywrightPage:
        page = self._pages.get(id(native))
        if page is None:
            page = self._pages[id(native)] = PlaywrightPage(native, self)
        return page

    def forget(self, native: PWPage) -> None:
        self._pages.pop(id(native), None)

    async def new_page(self) -> Result[Page, Exception]:
        created = await _attempt(self._native.new_page())
        return created.map(self._wrap)

    async def pages(self) -> Result[list[Page], Exception]:
        natives = self._native.pages
        live = {id(native) for native in natives}
        self._pages = {key: page for key, page in self._pages.items() if key in live}
        return Ok([self._wrap(native) for native in natives])

    async def close(self) -> Result[None, Exception]:
        closed = await _attempt(self._native.close())
        if closed.is_ok():
            self._pages.clear()
        return closed


def _blocking_handler(blocking: RequestBlocking) -> Callable[[Route], Awaitable[None]]:
    """A plain closure: Playwright and Patchright annotate a bound handler's
    ``__self__``, which frozen, slotted objects such as ``RequestBlocking``
    cannot accept."""

    async def handle(route: Route) -> None:
        request = route.request
        if blocking.blocks(request.resource_type, request.url):
            await route.abort()
        else:
            await route.continue_()

    return handle


async def _prepare_context(
    native: PWBrowserContext,
    options: BrowserContextOptions,
) -> Result[None, Exception]:
    """Apply the options that can be set on any context: timeouts and blocking."""

    if options.timeout is not None:
        native.set_default_timeout(options.timeout)
    if options.navigation_timeout is not None:
        native.set_default_navigation_timeout(options.navigation_timeout)
    if options.blocking is not None:
        routed = await _attempt(
            native.route("**/*", _blocking_handler(options.blocking))
        )
        if routed.is_error():
            return Error(routed.error)
    return Ok(None)


_DEFAULT_CONTEXT_OPTIONS = BrowserContextOptions()


def _unsupported_on_default_context(options: BrowserContextOptions) -> list[str]:
    """Options that only apply when a context is created, so an existing
    (default) context cannot honour them."""

    defaults = _DEFAULT_CONTEXT_OPTIONS
    return [
        name
        for name, value, default in (
            ("viewport", options.viewport, defaults.viewport),
            ("user_agent", options.user_agent, defaults.user_agent),
            ("proxy", options.proxy, defaults.proxy),
            ("locale", options.locale, defaults.locale),
            ("timezone_id", options.timezone_id, defaults.timezone_id),
            (
                "ignore_https_errors",
                options.ignore_https_errors,
                defaults.ignore_https_errors,
            ),
            (
                "java_script_enabled",
                options.java_script_enabled,
                defaults.java_script_enabled,
            ),
        )
        if value != default
    ]


class PlaywrightBrowser(LaunchedBrowser):
    """A launched (or connected) browser. Owned and closed by a ``BrowserSession``.

    With ``adopt_default_context``, the first :meth:`new_context` returns the
    browser's existing default context instead of creating one. A browser
    connected over CDP keeps its provider's fingerprint, extensions, and
    profile in that context.
    """

    def __init__(
        self,
        playwright: Playwright,
        native: PWBrowser,
        *,
        adopt_default_context: bool = False,
    ) -> None:
        self._playwright = playwright
        self._native = native
        self._closed = False
        self._adopt_default_context = adopt_default_context

    @property
    def native(self) -> PWBrowser:
        """The underlying Playwright browser (an escape hatch)."""

        return self._native

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        if self._closed:
            return Error(RuntimeError("browser is closed"))
        configured = options if options is not None else BrowserContextOptions()
        if self._adopt_default_context and self._native.contexts:
            self._adopt_default_context = False
            return await self._adopt(self._native.contexts[0], configured)
        viewport: ViewportSize | None = None
        if configured.viewport is not None:
            viewport = {
                "width": configured.viewport.width,
                "height": configured.viewport.height,
            }
        headers = configured.extra_http_headers
        created = await _attempt(
            self._native.new_context(
                viewport=viewport,
                permissions=(
                    list(configured.permissions)
                    if configured.permissions is not None
                    else None
                ),
                user_agent=configured.user_agent,
                extra_http_headers=dict(headers) if headers is not None else None,
                proxy=_proxy_settings(configured.proxy),
                locale=configured.locale,
                timezone_id=configured.timezone_id,
                ignore_https_errors=configured.ignore_https_errors,
                java_script_enabled=configured.java_script_enabled,
            )
        )
        if created.is_error():
            return Error(created.error)
        native = created.ok
        prepared = await _prepare_context(native, configured)
        if prepared.is_error():
            await _native_attempt(native.close())
            return Error(prepared.error)
        return Ok(PlaywrightBrowserContext(native))

    async def _adopt(
        self,
        native: PWBrowserContext,
        options: BrowserContextOptions,
    ) -> Result[BrowserContext, Exception]:
        unsupported = _unsupported_on_default_context(options)
        if unsupported:
            return Error(
                ValueError(
                    "the default context of a connected browser already exists; "
                    f"configure {', '.join(unsupported)} where it was launched"
                )
            )
        if options.permissions is not None:
            granted = await _attempt(
                native.grant_permissions(list(options.permissions))
            )
            if granted.is_error():
                return Error(granted.error)
        if options.extra_http_headers is not None:
            headers = await _attempt(
                native.set_extra_http_headers(dict(options.extra_http_headers))
            )
            if headers.is_error():
                return Error(headers.error)
        prepared = await _prepare_context(native, options)
        if prepared.is_error():
            return Error(prepared.error)
        return Ok(PlaywrightBrowserContext(native))

    async def close(self) -> None:
        """Close the browser (and every context and page in it)."""

        if self._closed:
            return
        self._closed = True
        try:
            await self._native.close()
        finally:
            await self._playwright.stop()


@dataclass(frozen=True, slots=True)
class PlaywrightDriver(BrowserDriver):
    """Launch browsers with Playwright or a Playwright-compatible package.

    ``package`` names any module that ships Playwright's ``async_api``, such
    as the Patchright stealth fork::

        BrowserSession(driver=PlaywrightDriver(package="patchright"))

    ``channel`` selects a branded build (``"chrome"``, ``"msedge"``) and
    ``executable_path`` a specific browser binary.

    ``cdp_url`` connects to a Chromium that is already running, such as a
    cloud browser, over the Chrome DevTools Protocol instead of launching
    one::

        PlaywrightDriver(package="patchright", cdp_url=session.ws_endpoint)

    The remote browser was configured where it was started, so
    ``BrowserOptions.headless``, ``args``, and ``proxy`` do not apply, and the
    session's first context is the browser's existing default context.
    Closing the session disconnects; stopping the remote browser is up to
    whoever started it.
    """

    package: str = "playwright"
    browser_type: BrowserTypeLiteral = "chromium"
    channel: str | None = None
    executable_path: Path | None = None
    cdp_url: str | None = None

    def __post_init__(self) -> None:
        if self.cdp_url is None:
            return
        if self.browser_type != "chromium":
            raise ValueError("cdp_url requires browser_type='chromium'")
        if self.channel is not None or self.executable_path is not None:
            raise ValueError(
                "cdp_url connects to a running browser; omit channel and executable_path"
            )

    async def launch(self, options: BrowserOptions) -> PlaywrightBrowser:
        if self.cdp_url is not None:
            return await self._connect(self.cdp_url, options)
        playwright = await self._async_playwright()().start()
        try:
            browser_types = {
                "chromium": playwright.chromium,
                "firefox": playwright.firefox,
                "webkit": playwright.webkit,
            }
            native = await browser_types[self.browser_type].launch(
                headless=options.headless,
                timeout=options.timeout,
                args=list(options.args),
                proxy=_proxy_settings(options.proxy),
                channel=self.channel,
                executable_path=self.executable_path,
            )
        except BaseException:
            await playwright.stop()
            raise
        return PlaywrightBrowser(playwright, native)

    async def _connect(
        self, cdp_url: str, options: BrowserOptions
    ) -> PlaywrightBrowser:
        if options.proxy is not None:
            raise ValueError(
                "a browser connected over CDP is not launched here; "
                "configure its proxy where it was started, or per context"
            )
        playwright = await self._async_playwright()().start()
        try:
            native = await playwright.chromium.connect_over_cdp(
                cdp_url,
                timeout=options.timeout,
            )
        except BaseException:
            await playwright.stop()
            raise
        return PlaywrightBrowser(playwright, native, adopt_default_context=True)

    def _async_playwright(self) -> Callable[[], _PlaywrightStarter]:
        if self.package == "playwright":
            return async_playwright
        module = import_module(f"{self.package}.async_api")
        # Compatible forks mirror Playwright's API under their own classes.
        return cast(Callable[[], _PlaywrightStarter], module.async_playwright)


__all__ = [
    "BrowserTypeLiteral",
    "PlaywrightBrowser",
    "PlaywrightBrowserContext",
    "PlaywrightDriver",
    "PlaywrightElementHandle",
    "PlaywrightFrame",
    "PlaywrightPage",
    "translate_error",
]
