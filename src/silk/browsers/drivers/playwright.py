"""
Playwright implementation of the browser driver and element handle for Silk.
"""

import logging
from pathlib import Path
import random
import asyncio
import string
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from expression import Error, Ok, Result
# We'll import these conditionally based on what's installed
# from playwright.async_api import Browser
# from playwright.async_api import BrowserContext as PlaywrightContext
# from playwright.async_api import ElementHandle as PlaywrightNativeElement
# from playwright.async_api import Page, Playwright
# from playwright.async_api import TimeoutError as PlaywrightTimeoutError
# from playwright.async_api import async_playwright

from silk.browsers.driver import BrowserDriver
from silk.browsers.element import ElementHandle
from silk.browsers.types import (
    BrowserOptions,
    CoordinateType,
    DragOptions,
    MouseButtonLiteral,
    MouseOptions,
    NavigationOptions,
    NavigationWaitLiteral,
    TypeOptions,
    WaitOptions,
)

logger = logging.getLogger(__name__)

ContextEntry = Tuple[str, Any]  # PlaywrightContext
PageEntry = Tuple[str, Any]  # Page


# Determine which driver to use
try:
    logger.info("Using patchright as the browser automation library")
    from patchright.async_api import Browser  # type: ignore
    from patchright.async_api import BrowserContext as PlaywrightContext  # type: ignore
    from patchright.async_api import ElementHandle as PlaywrightNativeElement  # type: ignore
    from patchright.async_api import Page, Playwright  # type: ignore
    from patchright.async_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
    from patchright.async_api import async_playwright  # type: ignore
except ImportError:
    logger.info("Using playwright as the browser automation library")
    from playwright.async_api import Browser  # type: ignore
    from playwright.async_api import BrowserContext as PlaywrightContext  # type: ignore
    from playwright.async_api import ElementHandle as PlaywrightNativeElement  # type: ignore
    from playwright.async_api import Page, Playwright  # type: ignore
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError  # type: ignore
    from playwright.async_api import async_playwright  # type: ignore

# TODO for ease of access all methods should accept both context and page,
# this avoids situations where some automation libraries need a page and others need a context
# ex we have pages[0]  instead of getting the page via page_id
class PlaywrightElementHandle(ElementHandle[PlaywrightNativeElement]):
    """
    Playwright implementation of the element handle.

    This class wraps a Playwright native element handle and implements
    the ElementHandle interface from Silk.
    """

    def __init__(
        self,
        driver: "PlaywrightDriver",
        page_id: str,
        element_ref: PlaywrightNativeElement,
        selector: Optional[str] = None,
    ):
        """Initialize a Playwright element handle."""
        super().__init__(driver, page_id, element_ref, selector)

    async def get_text(self) -> Result[str, Exception]:
        """Get the text content of this element."""
        try:
            # Use evaluate to get just this element's text content
            text = await self.element_ref.evaluate("el => el.textContent.trim()")
            return Ok(text or "")
        except Exception as e:
            logger.error(f"Error getting text: {e}")
            return Error(e)

    async def get_inner_text(self) -> Result[str, Exception]:
        """Get the innerText of this element."""
        try:
            inner_text = await self.element_ref.inner_text()
            return Ok(inner_text or "")
        except Exception as e:
            logger.error(f"Error getting inner text: {e}")
            return Error(e)

    async def get_html(self, outer: bool = True) -> Result[str, Exception]:
        """Get the HTML content of this element."""
        try:
            if outer:
                html = await self.element_ref.evaluate("el => el.outerHTML")
            else:
                html = await self.element_ref.evaluate("el => el.innerHTML")
            return Ok(html or "")
        except Exception as e:
            logger.error(f"Error getting HTML: {e}")
            return Error(e)

    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        """Get an attribute value from this element."""
        try:
            value = await self.element_ref.get_attribute(name)
            return Ok(value)
        except Exception as e:
            logger.error(f"Error getting attribute '{name}': {e}")
            return Error(e)

    async def get_property(self, name: str) -> Result[Any, Exception]:
        """Get a JavaScript property value from this element."""
        try:
            value = await self.element_ref.evaluate(f"el => el.{name}")
            return Ok(value)
        except Exception as e:
            logger.error(f"Error getting property '{name}': {e}")
            return Error(e)

    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        """Get the bounding box of this element."""
        try:
            box = await self.element_ref.bounding_box()
            if box is None:
                return Error(
                    Exception("Element is not visible or has been removed from DOM")
                )
            return Ok(
                {
                    "x": box["x"],
                    "y": box["y"],
                    "width": box["width"],
                    "height": box["height"],
                }
            )
        except Exception as e:
            logger.error(f"Error getting bounding box: {e}")
            return Error(e)

    async def click(self) -> Result[None, Exception]:
        """Click this element."""
        try:
            await self.element_ref.click()
            return Ok(None)
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return Error(e)

    async def fill(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Fill this element with the given text."""
        try:
            # First click on the element to ensure it's focused
            await self.element_ref.click()
            
            # Get the page associated with this element
            driver = cast(PlaywrightDriver, self.driver)
            page = driver.pages.get(self.page_id)
            if not page:
                return Error(Exception(f"Page with ID '{self.page_id}' not found"))
            
            # Create CDP session
            cdp_client = None  # Initialize cdp_client to None
            try:
                cdp_client = await page.context.new_cdp_session(page)
                if not cdp_client:
                    return Error(Exception("Failed to create CDP session"))

                # Characters requiring special keys
                shift_needed = ["!", '"', "#", "$", "%", "&", "'", "(", ")", "=", "?", "^", "*", "_", ":", ";", ">", "{", "}", "|", "~", "<", "+"]
                control_needed = ["@", "£", "€", "\\"]
                
                # Type each character with random delays
                for char in text:
                    special_key = None
                    
                    # Determine if we need a special key
                    if char in control_needed:
                        special_key = "Control"
                    elif char in shift_needed or char.isupper():
                        special_key = "Shift"
                    
                    # Press special key if needed
                    if special_key:
                        await cdp_client.send("Input.dispatchKeyEvent", {
                            "type": "keyDown",
                            "key": special_key,
                            "code": "ShiftLeft" if special_key == "Shift" else "ControlLeft",
                            "modifiers": 8 if special_key == "Shift" else 2
                        })
                        await asyncio.sleep(random.randint(50, 100) / 1000)
                    
                    # Key down event
                    await cdp_client.send("Input.dispatchKeyEvent", {
                        "type": "keyDown",
                        "text": char
                    })
                    
                    # Char event (actual typing)
                    await cdp_client.send("Input.dispatchKeyEvent", {
                        "type": "char",
                        "text": char
                    })
                    
                    # Hold key briefly
                    await asyncio.sleep(random.randint(50, 100) / 1000)
                    
                    # Key up event
                    await cdp_client.send("Input.dispatchKeyEvent", {
                        "type": "keyUp",
                        "text": char
                    })
                    
                    # Release special key if needed
                    if special_key:
                        await cdp_client.send("Input.dispatchKeyEvent", {
                            "type": "keyUp",
                            "key": special_key,
                            "code": "ShiftLeft" if special_key == "Shift" else "ControlLeft",
                            "modifiers": 8 if special_key == "Shift" else 2
                        })
                        await asyncio.sleep(random.randint(50, 100) / 1000)
                    
                    # Random delay between keystrokes
                    await asyncio.sleep(random.randint(50, 150) / 1000)
                
                return Ok(None)

            except Exception as e:
                logger.warning(f"CDP typing failed: {e}, falling back to standard fill")
                # Attempt fallback using standard fill, but re-query the element first
                if not self.selector:
                    logger.error("Cannot fallback to standard fill: Element selector is unknown.")
                    return Error(Exception("CDP fill failed and element selector is unknown for fallback."))

                try:
                    # Re-get the page in case the context changed subtly
                    driver = cast(PlaywrightDriver, self.driver)
                    page = driver.pages.get(self.page_id)
                    if not page:
                         return Error(Exception(f"Page with ID '{self.page_id}' not found for fallback fill"))

                    # Re-query the element using the stored selector
                    fresh_element = await page.query_selector(self.selector)
                    if not fresh_element:
                        logger.error(f"Cannot fallback to standard fill: Element '{self.selector}' not found after CDP failure.")
                        return Error(Exception(f"Element '{self.selector}' not found after CDP failure."))

                    # Use the fresh element handle for the standard fill
                    await fresh_element.fill(text)
                    return Ok(None)
                except Exception as inner_e:
                    logger.error(f"Fallback standard fill failed for element '{self.selector}': {inner_e}")
                    # Return the inner exception from the fallback attempt
                    return Error(inner_e)
            finally:
                # Ensure CDP session is detached regardless of success or failure
                if cdp_client:
                    try:
                        await cdp_client.detach()
                    except Exception as detach_e:
                        logger.warning(f"Failed to detach CDP session: {detach_e}")
        except Exception as e:
            logger.error(f"Error filling element: {e}")
            return Error(e)

    async def select(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        """Select an option from this element."""
        try:
            if value is not None:
                await self.element_ref.select_option(value=value)
            elif text is not None:
                await self.element_ref.select_option(label=text)
            else:
                return Error(Exception("Either value or text must be provided"))
            return Ok(None)
        except Exception as e:
            logger.error(f"Error selecting option: {e}")
            return Error(e)

    async def is_visible(self) -> Result[bool, Exception]:
        """Check if this element is visible."""
        try:
            return Ok(await self.element_ref.is_visible())
        except Exception as e:
            logger.error(f"Error checking visibility: {e}")
            return Error(e)

    async def is_enabled(self) -> Result[bool, Exception]:
        """Check if this element is enabled."""
        try:
            return Ok(await self.element_ref.is_enabled())
        except Exception as e:
            logger.error(f"Error checking if element is enabled: {e}")
            return Error(e)

    async def get_parent(self) -> Result[Optional[ElementHandle], Exception]:
        """Get the parent element."""
        try:
            parent = await self.element_ref.evaluate_handle("el => el.parentElement")
            # Check if the handle is null
            if parent is None or await parent.evaluate("handle => handle === null"):
                return Ok(None)

            # Cast to the correct type
            parent_element = cast(PlaywrightNativeElement, parent)
            return Ok(
                PlaywrightElementHandle(
                    driver=cast(PlaywrightDriver, self.driver),
                    page_id=self.page_id,
                    element_ref=parent_element,
                )
            )
        except Exception as e:
            logger.error(f"Error getting parent element: {e}")
            return Error(e)

    async def get_children(self) -> Result[list[ElementHandle], Exception]:
        """Get all child elements."""
        try:
            children = await self.element_ref.evaluate_handle(
                "el => Array.from(el.children)"
            )
            children_array = await children.evaluate("arr => arr.map((_, i) => i)")

            result_children: list[ElementHandle] = []
            for i in range(len(children_array)):
                child_handle = await children.evaluate_handle(f"arr => arr[{i}]")
                # Cast to the correct type
                child_element = cast(PlaywrightNativeElement, child_handle)
                result_children.append(
                    PlaywrightElementHandle(
                        driver=cast(PlaywrightDriver, self.driver),
                        page_id=self.page_id,
                        element_ref=child_element,
                    )
                )

            return Ok(result_children)
        except Exception as e:
            logger.error(f"Error getting child elements: {e}")
            return Error(e)

    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """Find a descendant element matching the selector."""
        try:
            element = await self.element_ref.query_selector(selector)
            if element is None:
                return Ok(None)

            return Ok(
                PlaywrightElementHandle(
                    driver=cast(PlaywrightDriver, self.driver),
                    page_id=self.page_id,
                    element_ref=element,
                    selector=selector,
                )
            )
        except Exception as e:
            logger.error(f"Error querying selector '{selector}': {e}")
            return Error(e)

    async def query_selector_all(
        self, selector: str
    ) -> Result[list[ElementHandle], Exception]:
        """Find all descendant elements matching the selector."""
        try:
            elements = await self.element_ref.query_selector_all(selector)
            result_elements: list[ElementHandle] = []

            for element in elements:
                result_elements.append(
                    PlaywrightElementHandle(
                        driver=cast(PlaywrightDriver, self.driver),
                        page_id=self.page_id,
                        element_ref=element,
                        selector=selector,
                    )
                )

            return Ok(result_elements)
        except Exception as e:
            logger.error(f"Error querying selector all '{selector}': {e}")
            return Error(e)

    async def scroll_into_view(self) -> Result[None, Exception]:
        """Scroll this element into view."""
        try:
            await self.element_ref.scroll_into_view_if_needed()
            return Ok(None)
        except Exception as e:
            logger.error(f"Error scrolling element into view: {e}")
            return Error(e)


class PlaywrightDriver(BrowserDriver):
    """
    Playwright implementation of the browser driver.
    """

    def __init__(self, options: BrowserOptions):
        """Initialize the Playwright driver with options."""
        super().__init__(options)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, PlaywrightContext] = {}
        self.pages: Dict[str, Page] = {}
        self.initialized = False
        self.options = options


    async def launch(self) -> Result[None, Exception]:
        """Launch the Playwright browser."""
        if self.initialized:
            return Ok(None)

        try:
            self.playwright = await async_playwright().start()

            browser_type = (
                self.options.browser_type if self.options.browser_type else "chromium"
            )

            # Prepare launch options as a proper dictionary
            launch_options: Dict[str, Any] = {
                "headless": self.options.headless,
            }

            # Add proxy if specified
            if self.options.proxy:
                launch_options["proxy"] = {"server": self.options.proxy}

            # Check if we need to connect to a remote browser
            if self.options.remote_url:
                logger.info(f"Connecting to remote browser at {self.options.remote_url}")
                if browser_type != "chromium":
                    logger.warning(f"Remote CDP connections only support Chromium. Ignoring browser_type={browser_type}")
                
                try:
                    # Connect to the remote browser via CDP
                    self.browser = await self.playwright.chromium.connect_over_cdp(
                        endpoint_url=self.options.remote_url,
                        timeout=self.options.timeout
                    )
                    logger.info("Successfully connected to remote browser")
                except Exception as e:
                    return Error(Exception(f"Failed to connect to remote browser: {e}"))
            else:
                # Launch the appropriate browser
                if browser_type == "chromium":
                    self.browser = await self.playwright.chromium.launch(**launch_options)
                elif browser_type == "firefox":
                    self.browser = await self.playwright.firefox.launch(**launch_options)
                elif browser_type == "webkit":
                    self.browser = await self.playwright.webkit.launch(**launch_options)
                else:
                    return Error(Exception(f"Unsupported browser type: {browser_type}"))

            self.initialized = True
            return Ok(None)

        except Exception as e:
            logger.error(f"Error launching browser: {e}")
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            return Error(e)

    async def close(self) -> Result[None, Exception]:
        """Close the Playwright browser."""
        try:
            for context_id in list(self.contexts.keys()):
                await self.close_context(context_id)

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.initialized = False
            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            return Error(e)

    async def create_context(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Result[str, Exception]:
        """Create a new browser context with isolated storage."""
        if not self.initialized or not self.browser:
            launch_result = await self.launch()
            if launch_result.is_error():
                return Error(launch_result.error)

        try:
            context_options: Dict[str, Any] = {}

            # Set viewport
            if self.options.viewport_width and self.options.viewport_height:
                context_options["viewport"] = {
                    "width": self.options.viewport_width,
                    "height": self.options.viewport_height,
                }

            # Set locale
            locale = self.options.locale
            if locale:
                context_options["locale"] = locale

            # Set timezone
            timezone = self.options.timezone
            if timezone:
                context_options["timezone_id"] = timezone

            # Set user agent
            user_agent = self.options.user_agent
            if user_agent:
                context_options["user_agent"] = user_agent

            # Merge additional options
            if options:
                context_options.update(options)

            # Create the context
            if not self.browser:
                return Error(Exception("Browser is not initialized"))

            context = await self.browser.new_context(**context_options)

            # Set default timeout
            if self.options.timeout:
                context.set_default_timeout(self.options.timeout)

            # Generate unique context ID
            context_id = f"context-{len(self.contexts) + 1}"
            self.contexts[context_id] = context

            return Ok(context_id)
        except Exception as e:
            logger.error(f"Error creating context: {e}")
            return Error(e)

    async def close_context(self, context_id: str) -> Result[None, Exception]:
        """Close a browser context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            # Remove all pages associated with this context
            pages_to_remove = []
            for page_id, page in self.pages.items():
                if page.context == context:
                    pages_to_remove.append(page_id)

            for page_id in pages_to_remove:
                self.pages.pop(page_id, None)

            # Close the context
            await context.close()
            self.contexts.pop(context_id, None)

            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing context: {e}")
            return Error(e)

    async def create_page(self, context_id: str) -> Result[str, Exception]:
        """Create a new page in the specified context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            # Create new page
            page = await context.new_page()

            # Set default timeout
            if self.options.timeout:
                page.set_default_timeout(self.options.timeout)

            # Generate unique page ID
            page_id = f"page-{len(self.pages) + 1}"
            self.pages[page_id] = page

            return Ok(page_id)
        except Exception as e:
            logger.error(f"Error creating page: {e}")
            return Error(e)

    async def close_page(self, page_id: str) -> Result[None, Exception]:
        """Close a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            # Close the page
            await page.close()
            self.pages.pop(page_id, None)

            return Ok(None)
        except Exception as e:
            logger.error(f"Error closing page: {e}")
            return Error(e)

    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate a page to a URL."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            goto_options: Dict[str, Any] = {}

            if options:
                # Set timeout if provided
                if options.timeout:
                    goto_options["timeout"] = options.timeout

                # Set wait_until if provided
                if options.wait_until:
                    # Map wait_until values to Playwright's expected values
                    goto_options["wait_until"] = options.wait_until

                # Set referer if provided
                if options.referer:
                    goto_options["referer"] = options.referer

            # Navigate to URL
            await page.goto(url, **goto_options)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout navigating to {url}: {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return Error(e)

    async def current_url(self, page_id: str) -> Result[str, Exception]:
        """Get the current URL of a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            return Ok(page.url)
        except Exception as e:
            logger.error(f"Error getting current URL: {e}")
            return Error(e)

    async def get_source(self, page_id: str) -> Result[str, Exception]:
        """Get the current page HTML source."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            html = await page.content()
            return Ok(html)
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return Error(e)

    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        """Take a screenshot of a page and save it to the specified path."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            screenshot_options: Dict[str, Any] = {}

            if path:
                screenshot_options["path"] = str(path)
                await page.screenshot(**screenshot_options)
                return Ok(path)
            else:
                screenshot_bytes = await page.screenshot()
                return Ok(screenshot_bytes)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return Error(e)

    async def reload(self, page_id: str) -> Result[None, Exception]:
        """Reload the current page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            await page.reload()
            return Ok(None)
        except Exception as e:
            logger.error(f"Error reloading page: {e}")
            return Error(e)

    async def go_back(self, page_id: str) -> Result[None, Exception]:
        """Go back to the previous page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            await page.go_back()
            return Ok(None)
        except Exception as e:
            logger.error(f"Error going back: {e}")
            return Error(e)

    async def go_forward(self, page_id: str) -> Result[None, Exception]:
        """Go forward to the next page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            await page.go_forward()
            return Ok(None)
        except Exception as e:
            logger.error(f"Error going forward: {e}")
            return Error(e)

    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """Query a single element with the provided selector in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            element = await page.query_selector(selector)
            if element is None:
                return Ok(None)

            return Ok(
                PlaywrightElementHandle(
                    driver=self, page_id=page_id, element_ref=element, selector=selector
                )
            )
        except Exception as e:
            logger.error(f"Error querying selector '{selector}': {e}")
            return Error(e)

    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[list[ElementHandle], Exception]:
        """Query all elements that match the provided selector in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            elements = await page.query_selector_all(selector)
            result_elements: list[ElementHandle] = []

            for element in elements:
                result_elements.append(
                    PlaywrightElementHandle(
                        driver=self,
                        page_id=page_id,
                        element_ref=element,
                        selector=selector,
                    )
                )

            return Ok(result_elements)
        except Exception as e:
            logger.error(f"Error querying selector all '{selector}': {e}")
            return Error(e)

    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        """Wait for an element matching the selector to appear in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            wait_options: Dict[str, Any] = {}

            if options:
                # Set timeout if provided
                if options.timeout:
                    wait_options["timeout"] = options.timeout

                # Set state if provided
                if options.state:
                    wait_options["state"] = options.state

            # Wait for selector
            element = await page.wait_for_selector(selector, **wait_options)
            if element is None:
                return Ok(None)

            return Ok(
                PlaywrightElementHandle(
                    driver=self, page_id=page_id, element_ref=element, selector=selector
                )
            )
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout waiting for selector '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error waiting for selector '{selector}': {e}")
            return Error(e)

    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Wait for navigation to complete in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            wait_until: NavigationWaitLiteral = "load"

            if options and options.wait_until:
                wait_until = options.wait_until

            # Set timeout
            timeout = None
            if options and options.timeout is not None:
                timeout = options.timeout

            # Wait for navigation to complete
            await page.wait_for_load_state(wait_until, timeout=timeout)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout waiting for navigation: {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error waiting for navigation: {e}")
            return Error(e)

    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Click an element in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            click_options: Dict[str, Any] = {}

            if options:
                # Set button if provided
                if options.button:
                    click_options["button"] = options.button

                # Set click_count if provided
                if hasattr(options, "click_count") and options.click_count is not None:
                    click_options["click_count"] = options.click_count

                # Set delay if provided
                delay = options.delay_between_ms
                if delay is not None:
                    click_options["delay"] = delay

                # Set timeout if provided
                if options.timeout:
                    click_options["timeout"] = options.timeout

                # Set force if provided
                force = options.force
                if force is not None:
                    click_options["force"] = force

            # Click the element
            await page.click(selector, **click_options)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout clicking element '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error clicking element '{selector}': {e}")
            return Error(e)

    async def double_click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Double click an element in a page."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            click_options: Dict[str, Any] = {}

            if options:
                # Set button if provided
                if options.button:
                    click_options["button"] = options.button

                # Set delay if provided
                delay = getattr(options, "delay_between_ms", None)
                if delay is not None:
                    click_options["delay"] = delay

                # Set timeout if provided
                if options.timeout:
                    click_options["timeout"] = options.timeout

                # Set force if provided
                force = getattr(options, "force", None)
                if force is not None:
                    click_options["force"] = force

                # Set position_offset if provided
                position_offset = getattr(options, "position_offset", None)
                if position_offset is not None:
                    click_options["position"] = {
                        "x": position_offset[0],
                        "y": position_offset[1],
                    }

            # Double-click the element
            await page.dblclick(selector, **click_options)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout double clicking element '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error double clicking element '{selector}': {e}")
            return Error(e)

    async def type(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """Type text into an element."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            type_options: Dict[str, Any] = {}

            if options:
                # Set delay if provided
                if options.delay is not None:
                    type_options["delay"] = options.delay

                # Set timeout if provided
                if options.timeout is not None:
                    type_options["timeout"] = options.timeout

            # Type the text
            await page.type(selector, text, **type_options)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout typing into element '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error typing into element '{selector}': {e}")
            return Error(e)

    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """Fill an input element with text."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            # Note: Playwright's fill() only accepts one optional parameter: force (boolean)
            timeout = None

            if options and options.timeout is not None:
                timeout = options.timeout

            # Fill the element
            await page.fill(selector, text, timeout=timeout)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout filling element '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error filling element '{selector}': {e}")
            return Error(e)

    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        """Select an option in a <select> element."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            select_options: Dict[str, Any] = {}

            if value is not None:
                select_options["value"] = value
            elif text is not None:
                select_options["label"] = text
            else:
                return Error(Exception("Either value or text must be provided"))

            # Select the option
            await page.select_option(selector, **select_options)
            return Ok(None)
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout selecting option in element '{selector}': {e}")
            return Error(e)
        except Exception as e:
            logger.error(f"Error selecting option in element '{selector}': {e}")
            return Error(e)

    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        """Execute JavaScript in the page context."""
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            # Execute the script
            result = await page.evaluate(script, *args)
            return Ok(result)
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return Error(e)

    async def mouse_move(
        self,
        context_id: str,
        x: float,
        y: float,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Move the mouse to the specified coordinates within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            move_options: Dict[str, Any] = {}
            if options and options.steps:
                move_options["steps"] = options.steps

            # Move the mouse
            await page.mouse.move(x, y, **move_options)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error moving mouse to ({x}, {y}): {e}")
            return Error(e)

    async def mouse_down(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Press a mouse button within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Press the mouse button
            await page.mouse.down(button=button)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error pressing mouse button '{button}': {e}")
            return Error(e)

    async def mouse_up(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Release a mouse button within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Release the mouse button
            await page.mouse.up(button=button)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error releasing mouse button '{button}': {e}")
            return Error(e)

    async def mouse_click(
        self,
        context_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Click at the current mouse position within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Press and release the mouse button
            await page.mouse.down(button=button)
            await page.mouse.up(button=button)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error clicking mouse button '{button}': {e}")
            return Error(e)

    async def mouse_double_click(
        self,
        context_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Double click at the specified coordinates within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            move_options: Dict[str, Any] = {}
            if options and options.steps:
                move_options["steps"] = options.steps

            # Move the mouse to the specified coordinates
            await page.mouse.move(x, y, **move_options)

            # Double click
            await page.mouse.dblclick(button="left", x=x, y=y)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error double clicking at ({x}, {y}): {e}")
            return Error(e)

    async def mouse_drag(
        self,
        context_id: str,
        source: Union[str, ElementHandle, CoordinateType],
        target: Union[str, ElementHandle, CoordinateType],
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """Drag from one element or position to another within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Get source coordinates
            source_x, source_y = await self._get_coordinates(page, source)
            if source_x is None or source_y is None:
                return Error(Exception("Could not determine source coordinates"))

            # Get target coordinates
            target_x, target_y = await self._get_coordinates(page, target)
            if target_x is None or target_y is None:
                return Error(Exception("Could not determine target coordinates"))

            # Get steps
            steps = 1
            if options and options.steps is not None:
                steps = options.steps

            # Perform the drag operation
            await page.mouse.move(source_x, source_y, steps=steps)
            await page.mouse.down()
            await page.mouse.move(target_x, target_y, steps=steps)
            await page.mouse.up()

            return Ok(None)
        except Exception as e:
            logger.error(f"Error dragging: {e}")
            return Error(e)

    async def key_press(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press a key or key combination within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            press_options: Dict[str, Any] = {}
            # Set delay if provided
            if options and hasattr(options, "delay") and options.delay is not None:
                press_options["delay"] = options.delay

            # Press the key
            await page.keyboard.press(key, **press_options)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error pressing key '{key}': {e}")
            return Error(e)

    async def key_down(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press and hold a key within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Press and hold the key
            await page.keyboard.down(key)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error pressing down key '{key}': {e}")
            return Error(e)

    async def key_up(
        self, context_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Release a key within a context."""
        try:
            context = self.contexts.get(context_id)
            if not context:
                return Error(Exception(f"Context with ID '{context_id}' not found"))

            pages = context.pages
            if not pages:
                return Error(Exception(f"No pages in context '{context_id}'"))

            page = pages[0]

            # Release the key
            await page.keyboard.up(key)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error releasing key '{key}': {e}")
            return Error(e)

    async def get_element_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """Get the text content of an element."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.get_text()
        except Exception as e:
            logger.error(f"Error getting element text: {e}")
            return Error(e)

    async def get_element_attribute(
        self, page_id: str, element: ElementHandle, name: str
    ) -> Result[Optional[str], Exception]:
        """Get an attribute value from an element."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.get_attribute(name)
        except Exception as e:
            logger.error(f"Error getting element attribute '{name}': {e}")
            return Error(e)

    async def get_element_bounding_box(
        self, page_id: str, element: ElementHandle
    ) -> Result[Dict[str, float], Exception]:
        """Get the bounding box of an element."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.get_bounding_box()
        except Exception as e:
            logger.error(f"Error getting element bounding box: {e}")
            return Error(e)

    async def click_element(
        self, page_id: str, element: ElementHandle
    ) -> Result[None, Exception]:
        """Click an element."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.click()
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return Error(e)

    async def get_element_html(
        self, page_id: str, element: ElementHandle, outer: bool = True
    ) -> Result[str, Exception]:
        """Get the HTML content of an element."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.get_html(outer)
        except Exception as e:
            logger.error(f"Error getting element HTML: {e}")
            return Error(e)

    async def get_element_inner_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """Get the innerText of an element (visible text only)."""
        try:
            if not isinstance(element, PlaywrightElementHandle):
                return Error(Exception("Element is not a PlaywrightElementHandle"))

            return await element.get_inner_text()
        except Exception as e:
            logger.error(f"Error getting element inner text: {e}")
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
        """Extract data from an HTML table element."""
        try:
            if not isinstance(table_element, PlaywrightElementHandle):
                return Error(
                    Exception("Table element is not a PlaywrightElementHandle")
                )

            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            headers = []
            if include_headers:
                header_elements_result = await table_element.query_selector_all(
                    header_selector
                )
                if header_elements_result.is_error():
                    return Error(header_elements_result.error)

                header_elements = header_elements_result.default_value([])

                for header_element in header_elements:
                    text_result = await header_element.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    header_text = text_result.default_value("").strip()
                    headers.append(header_text)

            rows_result = await table_element.query_selector_all(row_selector)
            if rows_result.is_error():
                return Error(rows_result.error)

            rows = rows_result.default_value([])

            table_data = []
            for row in rows:
                cells_result = await row.query_selector_all(cell_selector)
                if cells_result.is_error():
                    return Error(cells_result.error)

                cells = cells_result.default_value([])

                if len(cells) == 0:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    text_result = await cell.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    cell_text = text_result.default_value("").strip()

                    if include_headers and i < len(headers):
                        key = headers[i]
                    else:
                        key = f"col{i}"

                    row_data[key] = cell_text

                table_data.append(row_data)

            return Ok(table_data)
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return Error(e)

    async def scroll(
        self,
        page_id: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Result[None, Exception]:
        """
        Scroll the page to specific coordinates or scroll an element into view.

        Args:
            page_id: ID of the page to scroll
            x: Optional X coordinate to scroll to
            y: Optional Y coordinate to scroll to
            selector: Optional CSS selector of element to scroll into view
            options: Optional scroll behavior options

        Returns:
            Result indicating success or failure
        """
        try:
            page = self.pages.get(page_id)
            if not page:
                return Error(Exception(f"Page with ID '{page_id}' not found"))

            if selector is not None:
                # Scroll element into view
                element = await page.query_selector(selector)
                if element is None:
                    return Error(Exception(f"Element with selector '{selector}' not found"))
                
                await element.scroll_into_view_if_needed()
                return Ok(None)
            elif x is not None or y is not None:
                # Scroll to coordinates
                x_value = x if x is not None else 0
                y_value = y if y is not None else 0
                
                await page.evaluate(f"window.scrollTo({x_value}, {y_value});")
                return Ok(None)
            else:
                return Error(Exception("Either selector or coordinates (x, y) must be provided"))
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return Error(e)

    async def _get_coordinates(
        self, page: Page, target: Union[str, ElementHandle, CoordinateType]
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Helper method to get coordinates from various source types.

        Args:
            page: The page to work with
            target: A selector, element handle, or coordinate pair

        Returns:
            A tuple of (x, y) coordinates
        """
        if isinstance(target, tuple) and len(target) == 2:
            return target[0], target[1]

        elif isinstance(target, str):
            element = await page.query_selector(target)
            if element is None:
                return None, None

            box = await element.bounding_box()
            if box is None:
                return None, None

            return int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)

        elif isinstance(target, ElementHandle):
            if not isinstance(target, PlaywrightElementHandle):
                return None, None

            element_ref = target.element_ref
            box = await element_ref.bounding_box()
            if box is None:
                return None, None

            return int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2)

        return None, None

    async def execute_cdp_cmd(
        self, page_id: str, cmd: str, *args: Any
    ) -> Result[Any, Exception]:
        """
        Execute a CDP command
        """
        page = self.pages.get(page_id)
        if not page:
            return Error(Exception(f"Page with ID '{page_id}' not found"))

        cdp_client = await page.context.new_cdp_session(page)
        if not cdp_client:
            return Error(Exception("Failed to create CDP session"))

        result = await cdp_client.send(cmd, *args)
        return Ok(result)
