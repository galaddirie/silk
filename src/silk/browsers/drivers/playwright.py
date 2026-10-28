# pyright: strict
"""Playwright implementation of Silk's browser interfaces."""

from __future__ import annotations

from collections.abc import Awaitable
from pathlib import Path
from typing import Literal, TypeVar, overload
from uuid import uuid4

from fp_ops import Error, Ok, Result
from playwright.async_api import (
    Browser as PWBrowser,
    BrowserContext as PWBrowserContext,
    ElementHandle as PWElementHandle,
    FloatRect,
    Page as PWPage,
    Playwright,
    ProxySettings,
    ViewportSize,
    async_playwright,
)

from silk.browsers.models import (
    Browser,
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
    BrowserProxy,
    CoordinateType,
    ElementHandle,
    KeyModifier,
    MouseButtonLiteral,
    NavigationWaitLiteral,
    Page,
    WaitStateLiteral,
)
from silk.errors import DragElementMismatchError

T = TypeVar("T")

_NO_EVALUATION_ARGUMENT = object()
_MODIFIERS: dict[KeyModifier, Literal["Alt", "Control", "Meta", "Shift"]] = {
    KeyModifier.ALT: "Alt",
    KeyModifier.CTRL: "Control",
    KeyModifier.COMMAND: "Meta",
    KeyModifier.SHIFT: "Shift",
}


async def _attempt(awaitable: Awaitable[T]) -> Result[T, Exception]:
    """Await a Playwright call, turning ordinary exceptions into ``Error``."""

    try:
        return Ok(await awaitable)
    except Exception as error:
        return Error(error)


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
    ) -> Result[None, Exception]:
        return await _attempt(
            self._native.click(
                button=button,
                click_count=click_count,
                delay=delay_ms,
                timeout=timeout_ms,
                force=force,
                modifiers=_modifiers(modifiers),
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
            )
        )
        return navigated.map(lambda _response: None)

    async def url(self) -> Result[str, Exception]:
        return Ok(self.native.url)

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
            self.native.reload(wait_until=wait_until, timeout=timeout_ms)
        )
        return reloaded.map(lambda _response: None)

    async def go_back(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        moved = await _attempt(
            self.native.go_back(wait_until=wait_until, timeout=timeout_ms)
        )
        return moved.map(lambda _response: None)

    async def go_forward(
        self,
        *,
        timeout_ms: int | None = None,
        wait_until: NavigationWaitLiteral = "load",
    ) -> Result[None, Exception]:
        moved = await _attempt(
            self.native.go_forward(wait_until=wait_until, timeout=timeout_ms)
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

        return await _attempt(wait())

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


class PlaywrightBrowser(Browser):
    """A launched Chromium process. Owned and closed by a ``BrowserSession``."""

    def __init__(self, playwright: Playwright, native: PWBrowser) -> None:
        self._playwright = playwright
        self._native = native
        self._closed = False

    @classmethod
    async def launch(cls, options: BrowserOptions) -> PlaywrightBrowser:
        playwright = await async_playwright().start()
        try:
            native = await playwright.chromium.launch(
                headless=options.headless,
                timeout=options.timeout,
                args=list(options.args),
                proxy=_proxy_settings(options.proxy),
            )
        except BaseException:
            await playwright.stop()
            raise
        return cls(playwright, native)

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        if self._closed:
            return Error(RuntimeError("browser is closed"))
        configured = options if options is not None else BrowserContextOptions()
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
        if configured.timeout is not None:
            native.set_default_timeout(configured.timeout)
        if configured.navigation_timeout is not None:
            native.set_default_navigation_timeout(configured.navigation_timeout)
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


__all__ = [
    "PlaywrightBrowser",
    "PlaywrightBrowserContext",
    "PlaywrightElementHandle",
    "PlaywrightPage",
]
