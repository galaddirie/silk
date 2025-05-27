"""
Refactored Playwright implementation using ID-based architecture.
Instead of storing references to primitives, we use IDs and delegate to driver.
"""
from __future__ import annotations
import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast, Sequence, Literal, overload, TypedDict
from contextlib import asynccontextmanager
from weakref import WeakValueDictionary

# try:
#     from patchright.async_api import (
#         async_playwright,
#         Browser,
#         BrowserContext as PWBrowserContext,
#         Page as PWPage,
#         ElementHandle as PWElementHandle,
#         Playwright as PlaywrightAPIType,
#         Error as PlaywrightError,
#     )
# except ImportError:
from playwright.async_api import (
        async_playwright,
        Browser,
        BrowserContext as PWBrowserContext,
        Page as PWPage,
        ElementHandle as PWElementHandle,
        Playwright as PlaywrightAPIType,
        Error as PlaywrightError,
        FloatRect,
        Cookie,
    )
from expression import Error, Ok, Result

from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserOptions,
    CoordinateType,
    DragOptions,
    Driver,
    ElementHandle,
    MouseButton,
    MouseButtonLiteral,
    KeyModifier,
    KeyModifierLiteral,
    MouseOptions,
    NavigationOptions,
    Page,
    SelectOptions,
    TypeOptions,
    WaitOptions,
)
SetCookieParam = TypedDict("SetCookieParam", {
    "name": str,
    "value": str,
    "url": Optional[str],
    "domain": Optional[str],
    "path": Optional[str],
    "expires": Optional[float],
    "httpOnly": Optional[bool],
    "secure": Optional[bool],
    "sameSite": Optional[Literal["Lax", "None", "Strict"]],
})

class PlaywrightElementHandle(ElementHandle[PWElementHandle]):
    """Lightweight element handle that delegates to driver."""

    def __init__(
        self,
        driver: PlaywrightDriver,
        page_id: str,
        context_id: str,
        element_id: str,
        selector: Optional[str] = None,
    ):
        self.driver = driver
        self.page_id = page_id
        self.context_id = context_id
        self.element_id = element_id
        self.selector = selector
        self.element_ref = self.driver._get_element(self.element_id)



    def get_page_id(self) -> str:
        return self.page_id

    def get_context_id(self) -> str:
        return self.context_id

    def get_selector(self) -> Optional[str]:
        return self.selector

    def get_element_ref(self) -> PWElementHandle:
        """Get the actual element reference from driver when needed."""
        return self.driver._get_element(self.element_id)

    async def click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.click_element(self.page_id, self.element_id, options)

    async def double_click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.double_click_element(self.page_id, self.element_id, options)

    async def type(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.type_element(self.page_id, self.element_id, text, options)

    async def fill(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.fill_element(self.page_id, self.element_id, text, options)

    async def select(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        return await self.driver.select_element(self.page_id, self.element_id, value, text)

    async def get_text(self) -> Result[str, Exception]:
        return await self.driver.get_element_text(self.page_id, self.element_id)

    async def text(self) -> str:
        result = await self.get_text()
        return result.default_value("")

    async def get_inner_text(self) -> Result[str, Exception]:
        return await self.driver.get_element_inner_text(self.page_id, self.element_id)

    async def get_html(self, outer: bool = True) -> Result[str, Exception]:
        return await self.driver.get_element_html(self.page_id, self.element_id, outer)

    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        return await self.driver.get_element_attribute(self.page_id, self.element_id, name)

    async def attribute(self, name: str, default: str = "") -> str:
        result = await self.get_attribute(name)
        attr_value: Optional[str] = result.default_value(cast(str, ""))
        return attr_value if attr_value is not None else default

    async def has_attribute(self, name: str) -> bool:
        result = await self.get_attribute(name)
        attr_value: Optional[str] = result.default_value(cast(str, ""))
        return attr_value is not None

    async def get_property(self, name: str) -> Result[Any, Exception]:
        return await self.driver.get_element_property(self.page_id, self.element_id, name)

    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        return await self.driver.get_element_bounding_box(self.page_id, self.element_id)

    async def is_visible(self) -> Result[bool, Exception]:
        return await self.driver.is_element_visible(self.page_id, self.element_id)

    async def is_enabled(self) -> Result[bool, Exception]:
        return await self.driver.is_element_enabled(self.page_id, self.element_id)

    async def get_parent(self) -> Result[Optional["ElementHandle"], Exception]:
        return await self.driver.get_element_parent(self.page_id, self.element_id)

    async def get_children(self) -> Result[List["ElementHandle"], Exception]:
        return await self.driver.get_element_children(self.page_id, self.element_id)

    async def query_selector(
        self, selector: str
    ) -> Result[Optional["ElementHandle"], Exception]:
        return await self.driver.query_selector_from_element(
            self.page_id, self.element_id, selector
        )

    async def query_selector_all(
        self, selector: str
    ) -> Result[List["ElementHandle"], Exception]:
        return await self.driver.query_selector_all_from_element(
            self.page_id, self.element_id, selector
        )

    async def scroll_into_view(self) -> Result[None, Exception]:
        return await self.driver.scroll_element_into_view(self.page_id, self.element_id)

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

    def as_native(self) -> PWElementHandle:
        return self.get_element_ref()


class PlaywrightPage(Page[PWPage]):
    """Lightweight page that delegates to driver."""
    

    def __init__(
        self,
        driver: PlaywrightDriver,
        page_id: str,
        context_id: str,
    ):
        self.driver = driver
        self.page_id = page_id
        self.context_id = context_id
        self.page_ref = self.driver._get_page(self.page_id)



    def get_page_id(self) -> str:
        return self.page_id

    async def goto(
        self, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.goto(self.page_id, url, options)

    async def get_url(self) -> Result[str, Exception]:
        return await self.driver.current_url(self.page_id)

    async def current_url(self) -> Result[str, Exception]:
        return await self.get_url()

    async def get_title(self) -> Result[str, Exception]:
        return await self.driver.get_page_title(self.page_id)

    async def get_content(self) -> Result[str, Exception]:
        return await self.driver.get_source(self.page_id)

    async def get_page_source(self) -> Result[str, Exception]:
        return await self.get_content()
    
    async def set_content(self, content: str) -> Result[None, Exception]:
        return await self.driver.set_page_content(self.page_id, content)

    async def reload(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.reload(self.page_id, options)

    async def go_back(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.go_back(self.page_id, options)

    async def go_forward(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.go_forward(self.page_id, options)

    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        return await self.driver.query_selector(self.page_id, selector)

    async def query_selector_all(
        self, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        return await self.driver.query_selector_all(self.page_id, selector)

    async def wait_for_selector(
        self, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        return await self.driver.wait_for_selector(self.page_id, selector, options)

    async def wait_for_navigation(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.wait_for_navigation(self.page_id, options)

    async def click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.click(self.page_id, selector, options)

    async def double_click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.double_click(self.page_id, selector, options)

    async def type(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.type(self.page_id, selector, text, options)

    async def fill(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.fill(self.page_id, selector, text, options)

    async def select(
        self, selector: str, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        return await self.driver.select(self.page_id, selector, value, text)

    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        return await self.driver.execute_script(self.page_id, script, *args)

    @overload
    async def screenshot(
        self, path: Path
    ) -> Result[Path, Exception]:
        """Take a screenshot of the page and save it to a file."""
        ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]:
        """Take a screenshot of the page."""
        ...

    async def screenshot(
        self, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        return await self.driver.screenshot(self.page_id, path)

    async def mouse_move(
        self, x: float, y: float, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.mouse_move(self.page_id, x, y, options)

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        return await self.driver.mouse_down(self.page_id, button, options)

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        return await self.driver.mouse_up(self.page_id, button, options)

    async def mouse_click(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        return await self.driver.mouse_click(self.page_id, button, options)

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        return await self.driver.mouse_drag(self.page_id, source, target, options)

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.key_press(self.page_id, key, options)

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.key_down(self.page_id, key, options)

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        return await self.driver.key_up(self.page_id, key, options)

    async def close(self) -> Result[None, Exception]:
        return await self.driver.close_page(self.page_id)

    async def scroll(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
    ) -> Result[None, Exception]:
        return await self.driver.scroll(self.page_id, x, y, selector)


class PlaywrightBrowserContext(BrowserContext[PWBrowserContext]):
    """Lightweight browser context that delegates to driver."""

    def __init__(
        self,
        driver: PlaywrightDriver,
        context_id: str,
    ):
        self.driver = driver
        self.context_id = context_id
        self.page_id = ""
        self.context_ref = self.driver._get_context(self.context_id)



    def get_page_id(self) -> str:
        return self.page_id
    
    def get_context_id(self) -> str:
        return self.context_id

    async def new_page(self) -> Result[Page, Exception]:
        page_id_result = await self.driver.create_page(self.context_id)
        if page_id_result.is_error():
            return Error(page_id_result.error)
        page_id = page_id_result.default_value(None)
        if page_id is None:
            return Error(ValueError("Failed to create page"))
        page = PlaywrightPage(self.driver, page_id, self.context_id)
        return Ok(page)

    async def create_page(
        self, nickname: Optional[str] = None
    ) -> Result[Page, Exception]:
        return await self.new_page()

    async def pages(self) -> Result[List[Page], Exception]:
        return await self.driver.get_context_pages(self.context_id)

    async def get_page(
        self, page_id: Optional[str] = None
    ) -> Result[Page, Exception]:
        if page_id:
            return await self.driver.get_page(page_id)
        else:
            pages_result = await self.pages()
            if pages_result.is_error():
                return Error(pages_result.error)
            pages = pages_result.default_value([])
            if pages:
                return Ok(pages[0])
            return Error(ValueError("No pages available"))

    async def close_page(
        self, page_id: Optional[str] = None
    ) -> Result[None, Exception]:
        if page_id:
            return await self.driver.close_page(page_id)
        else:
            pages_result = await self.pages()
            if pages_result.is_ok():
                for page in pages_result.default_value([]):
                    await self.driver.close_page(page.page_id)
            return Ok(None)

    async def get_cookies(self) -> Result[List[Dict[str, Any]], Exception]:
        return await self.driver.get_context_cookies(self.context_id)

    async def set_cookies(
        self, cookies: List[Dict[str, Any]]
    ) -> Result[None, Exception]:
        return await self.driver.set_context_cookies(self.context_id, cookies)

    async def clear_cookies(self) -> Result[None, Exception]:
        return await self.driver.clear_context_cookies(self.context_id)

    async def add_init_script(self, script: str) -> Result[None, Exception]:
        return await self.driver.add_context_init_script(self.context_id, script)

    # Added missing set_content method
    async def set_content(self, content: str) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.set_page_content(page.page_id, content)

    async def mouse_move(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_move(page.page_id, x, y, options)

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_down(page.page_id, button, options)

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_up(page.page_id, button, options)

    async def mouse_click(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_click(page.page_id, button, options)

    async def mouse_double_click(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_double_click(page.page_id, x, y, options)

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.mouse_drag(page.page_id, source, target, options)

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.key_press(page.page_id, key, options)

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.key_down(page.page_id, key, options)

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        page_result = await self.get_page()
        if page_result.is_error():
            return Error(page_result.error)
        page = page_result.default_value(None)
        if page is None:
            return Error(ValueError("Failed to get page"))
        return await self.driver.key_up(page.page_id, key, options)

    async def close(self) -> Result[None, Exception]:
        return await self.driver.close_context(self.context_id)


class PlaywrightDriver(Driver[PlaywrightAPIType]):
    """Playwright driver with centralized reference management."""

    def __init__(self) -> None:
        self.driver_ref: Optional[PlaywrightAPIType] = None
        self.browser: Optional[Browser] = None
        
        self._contexts: Dict[str, PWBrowserContext] = {}
        self._pages: Dict[str, PWPage] = {}
        self._elements: WeakValueDictionary[str, PWElementHandle] = WeakValueDictionary()
        
        self._page_to_context: Dict[str, str] = {}
        self._element_to_page: Dict[str, str] = {}
        
        self._playwright_manager:Any = None

    def get_driver_ref(self) -> Optional[PlaywrightAPIType]:
        return self.driver_ref

    def _get_context(self, context_id: str) -> PWBrowserContext:
        """Get the actual Playwright context by ID."""
        context = self._contexts.get(context_id)
        if not context:
            raise ValueError(f"Context {context_id} not found")
        return context

    def _get_page(self, page_id: str) -> PWPage:
        """Get the actual Playwright page by ID."""
        page = self._pages.get(page_id)
        if not page:
            raise ValueError(f"Page {page_id} not found")
        return page

    def _get_element(self, element_id: str) -> PWElementHandle:
        """Get the actual Playwright element by ID."""
        element = self._elements.get(element_id)
        if not element:
            raise ValueError(f"Element {element_id} not found or has been garbage collected")
        return element

    def _register_element(self, element: PWElementHandle, page_id: str) -> str:
        """Register an element and return its ID."""
        element_id = str(uuid.uuid4())
        self._elements[element_id] = element
        self._element_to_page[element_id] = page_id
        return element_id

    async def launch(
        self, options: Optional[BrowserOptions] = None
    ) -> Result[None, Exception]:
        try:
            opts = options or BrowserOptions()
            
            self._playwright_manager = async_playwright()
            self.driver_ref = await self._playwright_manager.start()

            browser_launcher = {
                "chrome": self.driver_ref.chromium,
                "chromium": self.driver_ref.chromium,
                "firefox": self.driver_ref.firefox,
                "edge": self.driver_ref.chromium,
            }.get(opts.browser_type, self.driver_ref.chromium)

            # Fixed launch args handling
            launch_kwargs: Dict[str, Any] = {
                "headless": opts.headless,
            }
            
            if opts.browser_args:
                launch_kwargs["args"] = opts.browser_args
            
            if opts.proxy:
                launch_kwargs["proxy"] = {"server": opts.proxy}
            
            # Add other browser options as needed
            if opts.user_agent:
                launch_kwargs["user_agent"] = opts.user_agent
            
            if opts.ignore_https_errors:
                launch_kwargs["ignore_https_errors"] = opts.ignore_https_errors
            
            if opts.remote_url:
                # Fixed connect args handling
                connect_kwargs: Dict[str, Any] = {}
                if opts.timeout:
                    connect_kwargs["timeout"] = float(opts.timeout)
                if opts.extra_http_headers:
                    connect_kwargs["headers"] = opts.extra_http_headers
                
                self.browser = await browser_launcher.connect(
                    opts.remote_url,
                    **connect_kwargs
                )
            else:
                self.browser = await browser_launcher.launch(**launch_kwargs)
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def new_context(
        self, options: Optional[BrowserContextOptions] = None
    ) -> Result[BrowserContext, Exception]:
        try:
            if not self.browser:
                return Error(ValueError("Browser not launched"))
            
            context_options: Dict[str, Any] = {}
            if options:
                if options.viewport:
                    context_options["viewport"] = options.viewport
                if options.user_agent:
                    context_options["user_agent"] = options.user_agent
                if options.extra_http_headers:
                    context_options["extra_http_headers"] = options.extra_http_headers
                if options.proxy:
                    context_options["proxy"] = options.proxy
                if options.permissions:
                    context_options["permissions"] = options.permissions
                if options.user_data_dir:
                    context_options["user_data_dir"] = options.user_data_dir
                if options.args:
                    context_options["args"] = options.args
                # Note: headless is not a context option, it's a browser launch option
                if options.slow_mo:
                    context_options["slow_mo"] = options.slow_mo
                if options.timeout:
                    context_options["default_timeout"] = options.timeout
            
            pw_context = await self.browser.new_context(**context_options)
            
            context_id = str(uuid.uuid4())
            self._contexts[context_id] = pw_context
            
            context = PlaywrightBrowserContext(self, context_id)
            return Ok(context)
        except Exception as e:
            return Error(e)

    async def create_context(
        self, options: Optional[BrowserContextOptions] = None
    ) -> Result[str, Exception]:
        result = await self.new_context(options)
        if result.is_error():
            return Error(result.error)
        value = result.default_value(None)
        if value is None:
            return Error(ValueError("Failed to create context"))
        return Ok(value.context_id)

    async def contexts(self) -> Result[List[BrowserContext], Exception]:
        try:
            context_list: List[BrowserContext] = [
                PlaywrightBrowserContext(self, context_id)
                for context_id in self._contexts
            ]
            return Ok(context_list)
        except Exception as e:
            return Error(e)

    async def close_context(self, context_id: str) -> Result[None, Exception]:
        try:
            context = self._get_context(context_id)
            
            pages_to_close = [
                page_id for page_id, ctx_id in self._page_to_context.items()
                if ctx_id == context_id
            ]
            for page_id in pages_to_close:
                await self.close_page(page_id)
            
            await context.close()
            del self._contexts[context_id]
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def create_page(self, context_id: str) -> Result[str, Exception]:
        try:
            context = self._get_context(context_id)
            
            pw_page = await context.new_page()
            page_id = str(uuid.uuid4())
            self._pages[page_id] = pw_page
            self._page_to_context[page_id] = context_id
            
            return Ok(page_id)
        except Exception as e:
            return Error(e)

    async def get_page(self, page_id: str) -> Result[Page, Exception]:
        try:
            if page_id not in self._pages:
                return Error(ValueError(f"Page {page_id} not found"))
            
            context_id = self._page_to_context.get(page_id)
            if not context_id:
                return Error(ValueError(f"Context for page {page_id} not found"))
            
            page: Page = PlaywrightPage(self, page_id, context_id)
            return Ok(page)
        except Exception as e:
            return Error(e)

    async def get_context_pages(self, context_id: str) -> Result[List[Page], Exception]:
        try:
            pages: List[Page] = []
            for page_id, ctx_id in self._page_to_context.items():
                if ctx_id == context_id:
                    pages.append(PlaywrightPage(self, page_id, context_id))
            return Ok(pages)
        except Exception as e:
            return Error(e)

    async def close_page(self, page_id: str) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            
            elements_to_remove = [
                elem_id for elem_id, pg_id in self._element_to_page.items()
                if pg_id == page_id
            ]
            for elem_id in elements_to_remove:
                self._elements.pop(elem_id, None)
                del self._element_to_page[elem_id]
            
            await page.close()
            del self._pages[page_id]
            del self._page_to_context[page_id]
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or NavigationOptions()
            await page.goto(
                url,
                wait_until=opts.wait_until,
                timeout=opts.timeout,
                referer=opts.referer,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def current_url(self, page_id: str) -> Result[str, Exception]:
        try:
            page = self._get_page(page_id)
            return Ok(page.url)
        except Exception as e:
            return Error(e)

    async def get_page_title(self, page_id: str) -> Result[str, Exception]:
        try:
            page = self._get_page(page_id)
            title = await page.title()
            return Ok(title)
        except Exception as e:
            return Error(e)

    async def get_source(self, page_id: str) -> Result[str, Exception]:
        try:
            page = self._get_page(page_id)
            content = await page.content()
            return Ok(content)
        except Exception as e:
            return Error(e)
    
    async def set_page_content(self, page_id: str, content: str) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.set_content(content)
            return Ok(None)
        except Exception as e:
            return Error(e)
            
    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        try:
            page = self._get_page(page_id)
            if path:
                await page.screenshot(path=str(path))
                return Ok(path)
            else:
                data = await page.screenshot()
                return Ok(data)
        except Exception as e:
            return Error(e)

    async def reload(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or NavigationOptions()
            await page.reload(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def go_back(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or NavigationOptions()
            await page.go_back(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def go_forward(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or NavigationOptions()
            await page.go_forward(
                wait_until=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            page = self._get_page(page_id)
            element = await page.query_selector(selector)
            if element:
                context_id = self._page_to_context[page_id]
                element_id = self._register_element(element, page_id)
                handle: ElementHandle = PlaywrightElementHandle(
                    self, page_id, context_id, element_id, selector
                )
                return Ok(handle)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        try:
            page = self._get_page(page_id)
            elements = await page.query_selector_all(selector)
            context_id = self._page_to_context[page_id]
            handles: List[ElementHandle] = [
                PlaywrightElementHandle(
                    self, page_id, context_id,
                    self._register_element(el, page_id), selector
                )
                for el in elements
            ]
            return Ok(handles)
        except Exception as e:
            return Error(e)

    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or WaitOptions()
            element = await page.wait_for_selector(
                selector,
                state=opts.state,
                timeout=opts.timeout,
            )
            if element:
                context_id = self._page_to_context[page_id]
                element_id = self._register_element(element, page_id)
                handle: ElementHandle = PlaywrightElementHandle(
                    self, page_id, context_id, element_id, selector
                )
                return Ok(handle)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or NavigationOptions()
            await page.wait_for_load_state(
                state=opts.wait_until,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    # Fixed click_element method signature to match Driver protocol
    async def click_element(
        self, page_id: str, element: Union[ElementHandle, str], options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            opts = options or MouseOptions()
            await pw_element.click(
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

    async def double_click_element(
        self, page_id: str, element_id: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            element = self._get_element(element_id)
            opts = options or MouseOptions()
            await element.dblclick(
                button=opts.button,
                delay=opts.delay_between_ms,
                timeout=opts.timeout,
                force=True if opts.force > 0.5 else False,
                modifiers=self._get_modifiers(opts),
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def type_element(
        self,
        page_id: str,
        element_id: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        try:
            element = self._get_element(element_id)
            opts = options or TypeOptions()
            await element.type(
                text,
                delay=opts.delay,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def fill_element(
        self,
        page_id: str,
        element_id: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        try:
            element = self._get_element(element_id)
            opts = options or TypeOptions()
            if opts.clear:
                await element.fill("", timeout=opts.timeout)
            await element.fill(text, timeout=opts.timeout)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def select_element(
        self,
        page_id: str,
        element_id: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        try:
            element = self._get_element(element_id)
            if value:
                await element.select_option(value=value)
            elif text:
                await element.select_option(label=text)
            else:
                return Error(ValueError("Either value or text must be provided"))
            return Ok(None)
        except Exception as e:
            return Error(e)

    # Fixed get_element_text method signature to match Driver protocol
    async def get_element_text(
        self, page_id: str, element: Union[ElementHandle, str]
    ) -> Result[str, Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            text = await pw_element.text_content()
            return Ok(text or "")
        except Exception as e:
            return Error(e)

    # Fixed get_element_inner_text method signature to match Driver protocol
    async def get_element_inner_text(
        self, page_id: str, element: Union[ElementHandle, str]
    ) -> Result[str, Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            text = await pw_element.inner_text()
            return Ok(text)
        except Exception as e:
            return Error(e)

    # Fixed get_element_html method signature to match Driver protocol
    async def get_element_html(
        self, page_id: str, element: Union[ElementHandle, str], outer: bool = True
    ) -> Result[str, Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            if outer:
                html = await pw_element.evaluate("el => el.outerHTML")
            else:
                html = await pw_element.inner_html()
            return Ok(html)
        except Exception as e:
            return Error(e)

    # Fixed get_element_attribute method signature to match Driver protocol
    async def get_element_attribute(
        self, page_id: str, element: Union[ElementHandle, str], name: str
    ) -> Result[Optional[str], Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            attr = await pw_element.get_attribute(name)
            return Ok(attr)
        except Exception as e:
            return Error(e)

    async def get_element_property(
        self, page_id: str, element_id: str, name: str
    ) -> Result[Any, Exception]:
        try:
            element = self._get_element(element_id)
            prop = await element.get_property(name)
            value = await prop.json_value()
            return Ok(value)
        except Exception as e:
            return Error(e)

    # Fixed get_element_bounding_box method signature to match Driver protocol
    async def get_element_bounding_box(
        self, page_id: str, element: Union[ElementHandle, str]
    ) -> Result[Dict[str, float], Exception]:
        try:
            if isinstance(element, str):
                element_id = element
            else:
                # Extract element_id from ElementHandle
                if hasattr(element, 'element_id'):
                    element_id = element.element_id  # type: ignore
                else:
                    return Error(ValueError("Invalid element handle"))
            
            pw_element = self._get_element(element_id)
            box = await pw_element.bounding_box()
            if box:
                # Convert FloatRect to Dict[str, float]
                result: Dict[str, float] = {
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"]
                }
                return Ok(result)
            return Error(ValueError("Element has no bounding box"))
        except Exception as e:
            return Error(e)

    async def is_element_visible(
        self, page_id: str, element_id: str
    ) -> Result[bool, Exception]:
        try:
            element = self._get_element(element_id)
            visible = await element.is_visible()
            return Ok(visible)
        except Exception as e:
            return Error(e)

    async def is_element_enabled(
        self, page_id: str, element_id: str
    ) -> Result[bool, Exception]:
        try:
            element = self._get_element(element_id)
            enabled = await element.is_enabled()
            return Ok(enabled)
        except Exception as e:
            return Error(e)

    async def get_element_parent(
        self, page_id: str, element_id: str
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            element = self._get_element(element_id)
            parent = await element.evaluate_handle("el => el.parentElement")
            if parent:
                parent_element = cast(PWElementHandle, parent)
                context_id = self._page_to_context[page_id]
                parent_id = self._register_element(parent_element, page_id)
                handle: ElementHandle = PlaywrightElementHandle(
                    self, page_id, context_id, parent_id
                )
                return Ok(handle)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_element_children(
        self, page_id: str, element_id: str
    ) -> Result[List[ElementHandle], Exception]:
        try:
            element = self._get_element(element_id)
            children = await element.query_selector_all(":scope > *")
            context_id = self._page_to_context[page_id]
            handles: List[ElementHandle] = [
                PlaywrightElementHandle(
                    self, page_id, context_id,
                    self._register_element(child, page_id)
                )
                for child in children
            ]
            return Ok(handles)
        except Exception as e:
            return Error(e)

    async def query_selector_from_element(
        self, page_id: str, element_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        try:
            element = self._get_element(element_id)
            child = await element.query_selector(selector)
            if child:
                context_id = self._page_to_context[page_id]
                child_id = self._register_element(child, page_id)
                handle: ElementHandle = PlaywrightElementHandle(
                    self, page_id, context_id, child_id, selector
                )
                return Ok(handle)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def query_selector_all_from_element(
        self, page_id: str, element_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        try:
            element = self._get_element(element_id)
            children = await element.query_selector_all(selector)
            context_id = self._page_to_context[page_id]
            handles: List[ElementHandle] = [
                PlaywrightElementHandle(
                    self, page_id, context_id,
                    self._register_element(child, page_id), selector
                )
                for child in children
            ]
            return Ok(handles)
        except Exception as e:
            return Error(e)

    async def scroll_element_into_view(
        self, page_id: str, element_id: str
    ) -> Result[None, Exception]:
        try:
            element = self._get_element(element_id)
            await element.scroll_into_view_if_needed()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or MouseOptions()
            await page.click(
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
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or MouseOptions()
            await page.dblclick(
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
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or TypeOptions()
            await page.type(
                selector,
                text,
                delay=opts.delay,
                timeout=opts.timeout,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or TypeOptions()
            if opts.clear:
                await page.fill(selector, "", timeout=opts.timeout)
            await page.fill(selector, text, timeout=opts.timeout)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            if value:
                await page.select_option(selector, value=value)
            elif text:
                await page.select_option(selector, label=text)
            else:
                return Error(ValueError("Either value or text must be provided"))
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        try:
            page = self._get_page(page_id)
            result = await page.evaluate(script, *args)
            return Ok(result)
        except Exception as e:
            return Error(e)

    async def mouse_move(
        self,
        page_id: str,
        x: float,
        y: float,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or MouseOptions()
            await page.mouse.move(x, y, steps=opts.steps)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_down(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.mouse.down(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_up(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.mouse.up(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_click(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or MouseOptions()
            delay_ms = opts.delay_between_ms if opts.delay_between_ms is not None else 50
            await page.mouse.down(button=button, click_count=opts.click_count)
            await asyncio.sleep(delay_ms / 1000)
            await page.mouse.up(button=button, click_count=opts.click_count)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_double_click(
        self,
        page_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.mouse.move(x, y)
            opts = options or MouseOptions()
            await page.mouse.click(
                x, y,
                button="left",
                click_count=2,
                delay=opts.delay_between_ms,
            )
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def mouse_drag(
        self,
        page_id: str,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            opts = options or DragOptions()
            await page.mouse.move(source[0], source[1])
            await page.mouse.down()
            await page.mouse.move(
                target[0], target[1], steps=opts.steps
            )
            await page.mouse.up()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_press(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.keyboard.press(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_down(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.keyboard.down(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def key_up(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        try:
            page = self._get_page(page_id)
            await page.keyboard.up(key)
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def get_context_cookies(
        self, context_id: str
    ) -> Result[List[Dict[str, Any]], Exception]:
        try:
            context = self._get_context(context_id)
            cookies = await context.cookies()
            # Convert Cookie objects to Dict[str, Any]
            cookie_dicts: List[Dict[str, Any]] = [
                {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie.get("domain", ""),
                    "path": cookie.get("path", "/"),
                    "expires": cookie.get("expires", -1),
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                    "sameSite": cookie.get("sameSite", "Lax"),
                }
                for cookie in cookies
            ]
            return Ok(cookie_dicts)
        except Exception as e:
            return Error(e)

    async def set_context_cookies(
        self, context_id: str, cookies: List[Dict[str, Any]]
    ) -> Result[None, Exception]:
        try:
            context = self._get_context(context_id)
            # Convert Dict[str, Any] to SetCookieParam format
            cookie_params: List[SetCookieParam] = []
            for cookie_data in cookies:
                param: SetCookieParam = {
                    "name": cookie_data["name"],
                    "value": cookie_data["value"],
                    # Ensure all optional fields are correctly handled
                    "url": cookie_data.get("url"),
                    "domain": cookie_data.get("domain"),
                    "path": cookie_data.get("path"),
                    "expires": cookie_data.get("expires"),
                    "httpOnly": cookie_data.get("httpOnly"),
                    "secure": cookie_data.get("secure"),
                    "sameSite": cookie_data.get("sameSite"),
                }
                # Remove None values as Playwright expects missing keys for defaults
                param_cleaned = {k: v for k, v in param.items() if v is not None}
                cookie_params.append(cast(SetCookieParam, param_cleaned))
            
            await context.add_cookies(cookie_params) # type: ignore
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def clear_context_cookies(self, context_id: str) -> Result[None, Exception]:
        try:
            context = self._get_context(context_id)
            await context.clear_cookies()
            return Ok(None)
        except Exception as e:
            return Error(e)

    async def add_context_init_script(
        self, context_id: str, script: str
    ) -> Result[None, Exception]:
        try:
            context = self._get_context(context_id)
            await context.add_init_script(script)
            return Ok(None)
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
        try:
            page = self._get_page(page_id)
            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.scroll_into_view_if_needed()
            else:
                await page.evaluate(
                    f"window.scrollTo({x or 0}, {y or 0})"
                )
            return Ok(None)
        except Exception as e:
            return Error(e)

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
            # Extract element_id from ElementHandle
            if hasattr(table_element, 'element_id'):
                element_id = table_element.element_id  # type: ignore
            else:
                return Error(ValueError("Invalid table element handle"))
            
            # get the raw Playwright table handle
            table = self._get_element(element_id)
            
            print(f"DEBUG: Table element type: {type(table)}")
            print(f"DEBUG: Table element: {table}")

            # 1) Pull headers from the THEAD row only
            headers: List[str] = []
            if include_headers:
                thead_row = await table.query_selector("thead tr")
                print(f"DEBUG: Found thead row: {thead_row is not None}")
                
                if thead_row:
                    header_cells = await thead_row.query_selector_all(header_selector)
                    print(f"DEBUG: Found {len(header_cells)} header cells in thead")
                else:
                    header_cells = await table.query_selector_all(header_selector)
                    print(f"DEBUG: Using fallback - found {len(header_cells)} header cells")
                    
                for i, th in enumerate(header_cells):
                    text = await th.text_content()
                    cleaned_text = text.strip() if text else ""
                    headers.append(cleaned_text)
                    print(f"DEBUG: Header {i}: '{cleaned_text}'")

            print(f"DEBUG: Final headers: {headers}")

            # 2) Pull only the <tbody> rows
            data_rows = await table.query_selector_all(row_selector)
            print(f"DEBUG: Found {len(data_rows)} data rows")
            
            data: List[Dict[str, str]] = []

            # 3) For each body row, map each <td> to the corresponding header
            for row_idx, row in enumerate(data_rows):
                cells = await row.query_selector_all(cell_selector)
                print(f"DEBUG: Row {row_idx} has {len(cells)} cells")
                
                if not cells:
                    continue
                    
                row_dict: Dict[str, str] = {}
                for idx, cell in enumerate(cells):
                    text = await cell.text_content()
                    cleaned_text = text.strip() if text else ""
                    key = headers[idx] if idx < len(headers) else f"column_{idx}"
                    row_dict[key] = cleaned_text
                    print(f"DEBUG: Row {row_idx}, Cell {idx}: {key} = '{cleaned_text}'")
                    
                data.append(row_dict)

            print(f"DEBUG: Final data: {data}")
            return Ok(data)
        except Exception as e:
            print(f"DEBUG: Exception in extract_table: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return Error(e)

    async def execute_cdp_cmd(
        self, page_id: str, cmd: str, *args: Any
    ) -> Result[Any, Exception]:
        try:
            page = self._get_page(page_id)
            cdp_client = await page.context.new_cdp_session(page)
            if not cdp_client:
                return Error(Exception("Failed to create CDP session"))
            
            result = await cdp_client.send(cmd, *args)
            return Ok(result)
        except Exception as e:
            return Error(e)

    async def close(self) -> Result[None, Exception]:
        try:
            for context_id in list(self._contexts.keys()):
                await self.close_context(context_id)
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self._playwright_manager:
                await self._playwright_manager.__aexit__(None, None, None)
                self._playwright_manager = None
                self.driver_ref = None
            
            return Ok(None)
        except Exception as e:
            return Error(e)

    def _get_modifiers(self, options: MouseOptions) -> List[Literal["Alt", "Control", "Meta", "Shift"]]:
        """Convert KeyModifier enums to Playwright modifier strings."""
        modifiers: List[Literal["Alt", "Control", "Meta", "Shift"]] = []
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

    # Add missing function to fix no-untyped-def error
    def _setup_browser_options(self, options: BrowserOptions) -> Dict[str, Any]:
        """Setup browser launch options."""
        launch_options: Dict[str, Any] = {
            "headless": options.headless,
        }
        
        if options.browser_args:
            launch_options["args"] = options.browser_args
            
        if options.proxy:
            launch_options["proxy"] = {"server": options.proxy}
            
        if options.user_agent:
            launch_options["user_agent"] = options.user_agent
            
        if options.ignore_https_errors:
            launch_options["ignore_https_errors"] = options.ignore_https_errors
            

        return launch_options