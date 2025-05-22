"""
Playwright implementation of the browser automation protocols.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast
from contextlib import asynccontextmanager

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext as PWBrowserContext,
    Page as PWPage,
    ElementHandle as PWElementHandle,
    Playwright,
    Error as PlaywrightError,
)
from expression import Error, Ok, Result

from silk.browsers.types import (
    BrowserContext,
    BrowserOptions,
    CoordinateType,
    DragOptions,
    Driver,
    ElementHandle,
    MouseButton,
    MouseButtonLiteral,
    MouseOptions,
    NavigationOptions,
    Page,
    SelectOptions,
    TypeOptions,
    WaitOptions,
)

# TODO: store less references to the primitives, use ids + driver ref instead of page.method do driver.method(page_id)
# many element, page, and context helpers have symmetric counterparts in the driver with id parameters
# this will make the code more robust to refactoring and changes in the future
# it will also make the code more readable and easier to maintain
# it will also make the code more efficient by avoiding unnecessary references to the primitives


class PlaywrightElementHandle(ElementHandle):
    """Playwright implementation of ElementHandle protocol."""

    def __init__(
        self,
        driver: "PlaywrightDriver",
        page_id: str,
        context_id: str,
        element: PWElementHandle,
        selector: Optional[str] = None,
    ):
        self.driver = driver
        self.page_id = page_id
        self.context_id = context_id
        self.element_ref = element
        self.selector = selector

    def get_page_id(self) -> str:
        return self.page_id

    def get_context_id(self) -> str:
        return self.context_id

    def get_selector(self) -> Optional[str]:
        return self.selector

    def get_element_ref(self) -> PWElementHandle:
        return self.element_ref

    async def click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            await self.element_ref.click(
                button=opts.button,
                click_count=opts.click_count,
                delay=opts.delay_between_ms,
                timeout=opts.timeout,
                force=True if opts.force > 0.5 else False,
                modifiers=self._get_modifiers(opts),
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def double_click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            await self.element_ref.dblclick(
                button=opts.button,
                delay=opts.delay_between_ms,
                timeout=opts.timeout,
                force=True if opts.force > 0.5 else False,
                modifiers=self._get_modifiers(opts),
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def type(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or TypeOptions()
            await self.element_ref.type(
                text,
                delay=opts.delay,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def fill(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or TypeOptions()
            if opts.clear:
                await self.element_ref.fill("", timeout=opts.timeout)
            await self.element_ref.fill(text, timeout=opts.timeout)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def select(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        try:
            if value:
                await self.element_ref.select_option(value=value)
            elif text:
                await self.element_ref.select_option(label=text)
            else:
                return Error(ValueError("Either value or text must be provided"))
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_text(self) -> Result[str, Exception]:
        try:
            text = await self.element_ref.text_content()
            return Ok(text or "")
        except Exception as e:
            return Error(e)

    async def text(self) -> str:
        result = await self.get_text()
        return result.value if result.is_ok() else ""

    async def get_inner_text(self) -> Result[str, Exception]:
        try:
            text = await self.element_ref.inner_text()
            return Ok(text)
        except Exception as e:
            return Error(e)

    async def get_html(self, outer: bool = True) -> Result[str, Exception]:
        try:
            if outer:
                html = await self.element_ref.evaluate("el => el.outerHTML")
            else:
                html = await self.element_ref.inner_html()
            return Ok(html)
        except Exception as e:
            return Error(e)

    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        try:
            attr = await self.element_ref.get_attribute(name)
            return Ok(attr)
        except Exception as e:
            return Error(e)

    async def attribute(self, name: str, default: str = "") -> str:
        result = await self.get_attribute(name)
        if result.is_ok():
            return result.value or default
        return default

    async def has_attribute(self, name: str) -> bool:
        result = await self.get_attribute(name)
        return result.is_ok() and result.value is not None

    async def get_property(self, name: str) -> Result[Any, Exception]:
        try:
            prop = await self.element_ref.get_property(name)
            value = await prop.json_value()
            return Ok(value)
        except Exception as e:
            return Error(e)

    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        try:
            box = await self.element_ref.bounding_box()
            if box:
                return Ok(box)
            return Error(ValueError("Element has no bounding box"))
        except Exception as e:
            return Error(e)

    async def is_visible(self) -> Result[bool, Exception]:
        try:
            visible = await self.element_ref.is_visible()
            return Ok(visible)
        except Exception as e:
            return Error(e)

    async def is_enabled(self) -> Result[bool, Exception]:
        try:
            enabled = await self.element_ref.is_enabled()
            return Ok(enabled)
        except Exception as e:
            return Error(e)

    async def get_parent(self) -> Result[Optional[ElementHandle], Exception]:
        try:
            parent = await self.element_ref.evaluate_handle("el => el.parentElement")
            if parent:
                parent_element = cast(PWElementHandle, parent)
                return Ok(
                    PlaywrightElementHandle(
                        self.driver,
                        self.page_id,
                        self.context_id,
                        parent_element,
                    )
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_children(self) -> Result[List[ElementHandle], Exception]:
        try:
            children = await self.element_ref.query_selector_all("*")
            return Ok(
                [
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, child
                    )
                    for child in children
                ]
            )
        except Exception as e:
            return Error(e)

    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            element = await self.element_ref.query_selector(selector)
            if element:
                return Ok(
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, element, selector
                    )
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector_all(
        self, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        try:
            elements = await self.element_ref.query_selector_all(selector)
            return Ok(
                [
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, el, selector
                    )
                    for el in elements
                ]
            )
        except Exception as e:
            return Error(e)

    async def scroll_into_view(self) -> Result[None, Exception]:
        try:
            await self.element_ref.scroll_into_view_if_needed()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def input(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> "PlaywrightElementHandle":
        await self.fill(text, options)
        return self

    async def choose(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> "PlaywrightElementHandle":
        await self.select(value, text)
        return self

    @asynccontextmanager
    async def with_scroll_into_view(self):
        await self.scroll_into_view()
        yield self

    def as_native(self) -> PWElementHandle:
        return self.element_ref

    def _get_modifiers(self, options: MouseOptions) -> List[str]:
        """Convert KeyModifier enums to Playwright modifier strings."""
        modifiers = []
        for mod in options.modifiers:
            if mod.name == "ALT":
                modifiers.append("Alt")
            elif mod.name == "CTRL":
                modifiers.append("Control")
            elif mod.name == "COMMAND":
                modifiers.append("Meta")
            elif mod.name == "SHIFT":
                modifiers.append("Shift")
        return modifiers


class PlaywrightPage(Page):
    """Playwright implementation of Page protocol."""

    def __init__(
        self,
        driver: "PlaywrightDriver",
        page_id: str,
        context_id: str,
        page: PWPage,
    ):
        self.driver = driver
        self.page_id = page_id
        self.context_id = context_id
        self.page_ref = page

    def get_page_id(self) -> str:
        return self.page_id

    async def goto(
        self, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or NavigationOptions()
            await self.page_ref.goto(
                url,
                wait_until=opts.wait_until,
                timeout=opts.timeout,
                referer=opts.referer,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_url(self) -> Result[str, Exception]:
        try:
            return Ok(self.page_ref.url)
        except Exception as e:
            return Error(e)

    async def current_url(self) -> Result[str, Exception]:
        return await self.get_url()

    async def get_title(self) -> Result[str, Exception]:
        try:
            title = await self.page_ref.title()
            return Ok(title)
        except Exception as e:
            return Error(e)

    async def get_content(self) -> Result[str, Exception]:
        try:
            content = await self.page_ref.content()
            return Ok(content)
        except Exception as e:
            return Error(e)

    async def get_page_source(self) -> Result[str, Exception]:
        return await self.get_content()

    async def reload(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or NavigationOptions()
            await self.page_ref.reload(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def go_back(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or NavigationOptions()
            await self.page_ref.go_back(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def go_forward(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or NavigationOptions()
            await self.page_ref.go_forward(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            element = await self.page_ref.query_selector(selector)
            if element:
                return Ok(
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, element, selector
                    )
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector_all(
        self, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        try:
            elements = await self.page_ref.query_selector_all(selector)
            return Ok(
                [
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, el, selector
                    )
                    for el in elements
                ]
            )
        except Exception as e:
            return Error(e)

    async def wait_for_selector(
        self, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            opts = options or WaitOptions()
            element = await self.page_ref.wait_for_selector(
                selector,
                state=opts.state,
                timeout=opts.timeout,
            )
            if element:
                return Ok(
                    PlaywrightElementHandle(
                        self.driver, self.page_id, self.context_id, element, selector
                    )
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def wait_for_navigation(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or NavigationOptions()
            await self.page_ref.wait_for_load_state(
                state=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            await self.page_ref.click(
                selector,
                button=opts.button,
                click_count=opts.click_count,
                delay=opts.delay_between_ms,
                timeout=opts.timeout,
                force=True if opts.force > 0.5 else False,
                modifiers=self._get_modifiers(opts),
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def double_click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            await self.page_ref.dblclick(
                selector,
                button=opts.button,
                delay=opts.delay_between_ms,
                timeout=opts.timeout,
                force=True if opts.force > 0.5 else False,
                modifiers=self._get_modifiers(opts),
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def type(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or TypeOptions()
            await self.page_ref.type(
                selector,
                text,
                delay=opts.delay,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def fill(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or TypeOptions()
            if opts.clear:
                await self.page_ref.fill(selector, "", timeout=opts.timeout)
            await self.page_ref.fill(selector, text, timeout=opts.timeout)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def select(
        self, selector: str, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        try:
            if value:
                await self.page_ref.select_option(selector, value=value)
            elif text:
                await self.page_ref.select_option(selector, label=text)
            else:
                return Error(ValueError("Either value or text must be provided"))
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        try:
            result = await self.page_ref.evaluate(script, *args)
            return Ok(result)
        except Exception as e:
            return Error(e)

    async def screenshot(
        self, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        try:
            if path:
                await self.page_ref.screenshot(path=str(path))
                return Ok(path)
            else:
                data = await self.page_ref.screenshot()
                return Ok(data)
        except Exception as e:
            return Error(e)

    async def mouse_move(
        self, x: float, y: float, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            await self.page_ref.mouse.move(x, y, steps=opts.steps)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            await self.page_ref.mouse.down(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            await self.page_ref.mouse.up(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_click(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            opts = options or MouseOptions()
            # Get current position
            pos = await self.page_ref.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
            await self.page_ref.mouse.click(
                pos["x"], 
                pos["y"], 
                button=button,
                click_count=opts.click_count,
                delay=opts.delay_between_ms,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        try:
            opts = options or DragOptions()
            await self.page_ref.mouse.move(source[0], source[1])
            await self.page_ref.mouse.down()
            await self.page_ref.mouse.move(
                target[0], target[1], steps=opts.steps
            )
            await self.page_ref.mouse.up()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            await self.page_ref.keyboard.press(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            await self.page_ref.keyboard.down(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            await self.page_ref.keyboard.up(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def close(self) -> Result[None, Exception]:
        try:
            await self.page_ref.close()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def scroll(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
    ) -> Result[None, Exception]:
        try:
            if selector:
                element = await self.page_ref.query_selector(selector)
                if element:
                    await element.scroll_into_view_if_needed()
            else:
                await self.page_ref.evaluate(
                    f"window.scrollTo({x or 0}, {y or 0})"
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

    def _get_modifiers(self, options: MouseOptions) -> List[str]:
        """Convert KeyModifier enums to Playwright modifier strings."""
        modifiers = []
        for mod in options.modifiers:
            if mod.name == "ALT":
                modifiers.append("Alt")
            elif mod.name == "CTRL":
                modifiers.append("Control")
            elif mod.name == "COMMAND":
                modifiers.append("Meta")
            elif mod.name == "SHIFT":
                modifiers.append("Shift")
        return modifiers


class PlaywrightBrowserContext(BrowserContext):
    """Playwright implementation of BrowserContext protocol."""

    def __init__(
        self,
        driver: "PlaywrightDriver",
        context_id: str,
        context: PWBrowserContext,
    ):
        self.driver = driver
        self.context_id = context_id
        self.context_ref = context
        self.page_id = ""  # Not used for context

    def get_page_id(self) -> str:
        return self.page_id

    async def new_page(self) -> Result[Page, Exception]:
        try:
            pw_page = await self.context_ref.new_page()
            page_id = str(uuid.uuid4())
            page = PlaywrightPage(self.driver, page_id, self.context_id, pw_page)
            self.driver._pages[page_id] = page
            return Ok(page)
        except Exception as e:
            return Error(e)

    async def create_page(
        self, nickname: Optional[str] = None
    ) -> Result[Page, Exception]:
        return await self.new_page()

    # todo: improve this
    async def pages(self) -> Result[List[Page], Exception]:
        try:
            pw_pages = self.context_ref.pages
            pages = []
            for pw_page in pw_pages:
                # Find or create page wrapper
                page_found = False
                for page_id, page in self.driver._pages.items():
                    if page.page_ref == pw_page:
                        pages.append(page)
                        page_found = True
                        break
                if not page_found:
                    # Create new wrapper for untracked page
                    page_id = str(uuid.uuid4())
                    page = PlaywrightPage(
                        self.driver, page_id, self.context_id, pw_page
                    )
                    self.driver._pages[page_id] = page
                    pages.append(page)
            return Ok(pages)
        except Exception as e:
            return Error(e)

    async def get_page(
        self, page_id: Optional[str] = None
    ) -> Result[Page, Exception]:
        try:
            if page_id:
                page = self.driver._pages.get(page_id)
                if page:
                    return Ok(page)
                return Error(ValueError(f"Page {page_id} not found"))
            else:
                # Return first page
                pages_result = await self.pages()
                if pages_result.is_error():
                    return pages_result
                pages = pages_result.value
                if pages:
                    return Ok(pages[0])
                return Error(ValueError("No pages available"))
        except Exception as e:
            return Error(e)

    async def close_page(
        self, page_id: Optional[str] = None
    ) -> Result[None, Exception]:
        try:
            if page_id:
                page = self.driver._pages.get(page_id)
                if page:
                    await page.close()
                    del self.driver._pages[page_id]
                    return Ok(None)
                return Error(ValueError(f"Page {page_id} not found"))
            else:
                # Close all pages
                for page in list(self.driver._pages.values()):
                    if page.context_id == self.context_id:
                        await page.close()
                        del self.driver._pages[page.page_id]
                return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_cookies(self) -> Result[List[Dict[str, Any]], Exception]:
        try:
            cookies = await self.context_ref.cookies()
            return Ok(cookies)
        except Exception as e:
            return Error(e)

    async def set_cookies(
        self, cookies: List[Dict[str, Any]]
    ) -> Result[None, Exception]:
        try:
            await self.context_ref.add_cookies(cookies)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def clear_cookies(self) -> Result[None, Exception]:
        try:
            await self.context_ref.clear_cookies()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def add_init_script(self, script: str) -> Result[None, Exception]:
        try:
            await self.context_ref.add_init_script(script)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_move(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        # Get the first page to perform mouse operations
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.mouse_move(x, y, options)

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.mouse_down(button, options)

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.mouse_up(button, options)

    async def mouse_click(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.mouse_click(button, options)

    async def mouse_double_click(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        await page.mouse_move(x, y, options)
        opts = options or MouseOptions()
        opts.click_count = 2
        return await page.mouse_click("left", opts)

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.mouse_drag(source, target, options)

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.key_press(key, options)

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.key_down(key, options)

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return page_result
        page = page_result.value
        return await page.key_up(key, options)

    async def close(self) -> Result[None, Exception]:
        try:
            # Close all pages first
            await self.close_page()
            # Then close context
            await self.context_ref.close()
            return Ok(None)
        except Exception as e:
            return Error(e)


class PlaywrightDriver(Driver):
    """Playwright implementation of Driver protocol."""

    def __init__(self):
        self.driver_ref: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, PlaywrightBrowserContext] = {}
        self._pages: Dict[str, PlaywrightPage] = {}
        self._playwright_manager = None

    def get_driver_ref(self) -> Optional[Playwright]:
        return self.driver_ref

    async def launch(
        self, options: Optional[BrowserOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or BrowserOptions()
            
            # Start playwright
            self._playwright_manager = async_playwright()
            self.driver_ref = await self._playwright_manager.start()

            # Choose browser
            browser_launcher = {
                "chrome": self.driver_ref.chromium,
                "chromium": self.driver_ref.chromium,
                "firefox": self.driver_ref.firefox,
                "edge": self.driver_ref.chromium,
            }.get(opts.browser_type, self.driver_ref.chromium)

            # Launch browser
            launch_args = {
                "headless": opts.headless,
                "args": opts.browser_args,
            }
            
            if opts.proxy:
                launch_args["proxy"] = {"server": opts.proxy}
            
            if opts.remote_url:
                # Connect to remote browser
                self.browser = await browser_launcher.connect(
                    opts.remote_url,
                    **launch_args
                )
            else:
                # Launch local browser
                self.browser = await browser_launcher.launch(**launch_args)
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def new_context(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Result[BrowserContext, Exception]:
        try:
            if not self.browser:
                return Error(ValueError("Browser not launched"))
            
            context_options = options or {}
            
            # Create browser context
            pw_context = await self.browser.new_context(**context_options)
            
            context_id = str(uuid.uuid4())
            context = PlaywrightBrowserContext(self, context_id, pw_context)
            self.contexts[context_id] = context
            
            return Ok(context)
        except Exception as e:
            return Error(e)

    async def create_context(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Result[str, Exception]:
        result = await self.new_context(options)
        if result.is_error():
            return Error(result.error)
        return Ok(result.value.context_id)

    async def contexts(self) -> Result[List[BrowserContext], Exception]:
        try:
            return Ok(list(self.contexts.values()))
        except Exception as e:
            return Error(e)

    async def close_context(self, context_id: str) -> Result[None, Exception]:
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(ValueError(f"Context {context_id} not found"))
            
            await context.close()
            del self.contexts[context_id]
            
            # Remove pages associated with this context
            pages_to_remove = [
                page_id
                for page_id, page in self._pages.items()
                if page.context_id == context_id
            ]
            for page_id in pages_to_remove:
                del self._pages[page_id]
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def create_page(self, context_id: str) -> Result[str, Exception]:
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(ValueError(f"Context {context_id} not found"))
            
            page_result = await context.new_page()
            if page_result.is_error():
                return Error(page_result.error)
            
            return Ok(page_result.value.page_id)
        except Exception as e:
            return Error(e)

    async def close_page(self, page_id: str) -> Result[None, Exception]:
        try:
            page = self._pages.get(page_id)
            if not page:
                return Error(ValueError(f"Page {page_id} not found"))
            
            await page.close()
            del self._pages[page_id]
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.goto(url, options)

    async def current_url(self, page_id: str) -> Result[str, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.get_url()

    async def get_source(self, page_id: str) -> Result[str, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.get_content()

    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.screenshot(path)

    async def reload(self, page_id: str) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.reload()

    async def go_back(self, page_id: str) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.go_back()

    async def go_forward(self, page_id: str) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.go_forward()

    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.query_selector(selector)

    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.query_selector_all(selector)

    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.wait_for_selector(selector, options)

    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.wait_for_navigation(options)

    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.click(selector, options)

    async def double_click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.double_click(selector, options)

    async def type(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.type(selector, text, options)

    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.fill(selector, text, options)

    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.select(selector, value, text)

    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.execute_script(script, *args)

    async def mouse_move(
        self,
        page_id: str,
        x: float,
        y: float,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.mouse_move(x, y, options)

    async def mouse_down(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.mouse_down(button, options)

    async def mouse_up(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.mouse_up(button, options)

    async def mouse_click(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.mouse_click(button, options)

    async def mouse_double_click(
        self,
        page_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        await page.mouse_move(x, y, options)
        opts = options or MouseOptions()
        opts.click_count = 2
        return await page.mouse_click("left", opts)

    async def mouse_drag(
        self,
        page_id: str,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.mouse_drag(source, target, options)

    async def key_press(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.key_press(key, options)

    async def key_down(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.key_down(key, options)

    async def key_up(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.key_up(key, options)

    async def get_element_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        return await element.get_text()

    async def get_element_attribute(
        self, page_id: str, element: ElementHandle, name: str
    ) -> Result[Optional[str], Exception]:
        return await element.get_attribute(name)

    async def get_element_bounding_box(
        self, page_id: str, element: ElementHandle
    ) -> Result[Dict[str, float], Exception]:
        return await element.get_bounding_box()

    async def click_element(
        self, page_id: str, element: ElementHandle
    ) -> Result[None, Exception]:
        return await element.click()

    async def get_element_html(
        self, page_id: str, element: ElementHandle, outer: bool = True
    ) -> Result[str, Exception]:
        return await element.get_html(outer)

    async def get_element_inner_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        return await element.get_inner_text()

    async def extract_table(
        self,
        page_id: str,
        table_element: ElementHandle,
        include_headers: bool = True,
        header_selector: str = "th",
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> Result[List[Dict[str, str]], Exception]:
        try:
            # Get native element
            table = table_element.as_native()
            
            # Extract headers if needed
            headers = []
            if include_headers:
                header_elements = await table.query_selector_all(header_selector)
                for header in header_elements:
                    text = await header.text_content()
                    headers.append(text.strip() if text else "")
            
            # Extract rows
            rows = await table.query_selector_all(row_selector)
            data = []
            
            for row in rows:
                cells = await row.query_selector_all(cell_selector)
                if not cells:
                    continue
                
                row_data = {}
                for i, cell in enumerate(cells):
                    text = await cell.text_content()
                    key = headers[i] if i < len(headers) else f"column_{i}"
                    row_data[key] = text.strip() if text else ""
                
                if row_data:
                    data.append(row_data)
            
            return Ok(data)
        except Exception as e:
            return Error(e)

    async def scroll(
        self,
        page_id: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Result[None, Exception]:
        page = self._pages.get(page_id)
        if not page:
            return Error(ValueError(f"Page {page_id} not found"))
        return await page.scroll(x, y, selector)

    async def execute_cdp_cmd(
        self, page_id: str, cmd: str, *args: Any
    ) -> Result[Any, Exception]:
        """
        Execute a CDP command
        """
        page = self._pages.get(page_id)
        if not page:
            return Error(Exception(f"Page with ID '{page_id}' not found"))

        cdp_client = await page.page_ref.context.new_cdp_session(page)
        if not cdp_client:
            return Error(Exception("Failed to create CDP session"))

        result = await cdp_client.send(cmd, *args)
        return Ok(result)

    async def close(self) -> Result[None, Exception]:
        try:
            # Close all contexts
            for context in list(self.contexts.values()):
                await context.close()
            self.contexts.clear()
            self._pages.clear()
            
            # Close browser
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            # Stop playwright
            if self._playwright_manager:
                await self._playwright_manager.__aexit__(None, None, None)
                self._playwright_manager = None
                self.driver_ref = None
            
            return Ok(None)
        except Exception as e:
            return Error(e)


# Register the driver
def register_playwright_driver():
    """Register the Playwright driver with the driver registry."""
    from silk.browsers.registry import DriverRegistry
    DriverRegistry.register("playwright", PlaywrightDriver)