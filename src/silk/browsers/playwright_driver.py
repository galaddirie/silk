from typing import Optional, List, Any, Dict, cast, Literal, Union, Mapping
from pathlib import Path
import asyncio
from patchright.async_api import async_playwright, Browser, Page, ElementHandle as PlaywrightElement, Playwright, ProxySettings

from expression.core import Result, Ok, Error
from silk.browsers.driver import BrowserDriver, BrowserOptions, ElementHandle
from silk.actions.decorators import action

class PlaywrightElementHandle(ElementHandle):
    """Implementation of ElementHandle for Playwright"""
    
    def __init__(self, element: PlaywrightElement):
        self.element = element
    
    async def click(self) -> Result[None, Exception]:
        try:
            await self.element.click()
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def fill(self, text: str, delay: Optional[float] = None) -> Result[None, Exception]:
        try:
            await self.element.fill(text)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def get_text(self) -> Result[str, Exception]:
        try:
            return Ok(await self.element.text_content() or "")
        except Exception as e:
            return Error(e)
    
    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        try:
            return Ok(await self.element.get_attribute(name))
        except Exception as e:
            return Error(e)
    
    async def is_visible(self) -> Result[bool, Exception]:
        try:
            return Ok(await self.element.is_visible())
        except Exception as e:
            return Error(e)


class PlaywrightDriver(BrowserDriver[PlaywrightElementHandle]):
    """Implementation of BrowserDriver using Playwright"""
    
    def __init__(self, options: BrowserOptions):
        super().__init__(options)
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def launch(self) -> Result[None, Exception]:
        try:
            self.playwright = await async_playwright().start()
            
            if self.playwright is None:
                return Error(Exception("Failed to initialize playwright"))
                
            # Configure browser launch options
            browser_type = self.playwright.chromium
            launch_options: Dict[str, Any] = {
                "headless": self.options.headless
            }
            
            if self.options.proxy:
                # Create a proper ProxySettings object
                proxy_settings: ProxySettings = {"server": self.options.proxy}
                launch_options["proxy"] = proxy_settings
            
            # Add extra arguments if any
            if self.options.extra_args:
                launch_options.update(self.options.extra_args)
            
            self.browser = await browser_type.launch(**launch_options)
            
            if self.browser is None:
                return Error(Exception("Failed to launch browser"))
                
            self.page = await self.browser.new_page()
            
            if self.page is None:
                return Error(Exception("Failed to create new page"))
                
            # Configure page
            await self.page.set_viewport_size({
                "width": self.options.viewport_width,
                "height": self.options.viewport_height
            })
            
            # Set user agent if it exists in extra_args
            user_agent = self.options.extra_args.get("user_agent")
            if user_agent and isinstance(user_agent, str):
                await self.page.set_extra_http_headers({"User-Agent": user_agent})
            
            # Set cookies if they exist in extra_args
            cookies = self.options.extra_args.get("cookies")
            if cookies and isinstance(cookies, list):
                await self.page.context.add_cookies(cookies)
            
            # Set default timeout
            self.page.set_default_timeout(self.options.timeout)
            
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def close(self) -> Result[None, Exception]:
        try:
            if self.browser:
                await self.browser.close()
            
            if self.playwright:
                await self.playwright.stop()
                
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def goto(self, url: str) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.goto(url, wait_until="networkidle")
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def current_url(self) -> Result[str, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            return Ok(self.page.url)
        except Exception as e:
            return Error(e)
    
    async def get_page_source(self) -> Result[str, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            return Ok(await self.page.content())
        except Exception as e:
            return Error(e)
    
    async def take_screenshot(self, path: Path) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.screenshot(path=str(path))
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def query_selector(self, selector: str) -> Result[Optional[PlaywrightElementHandle], Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            element = await self.page.query_selector(selector)
            if element:
                return Ok(PlaywrightElementHandle(element))
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def query_selector_all(self, selector: str) -> Result[List[ElementHandle], Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            elements = await self.page.query_selector_all(selector)
            return Ok([PlaywrightElementHandle(element) for element in elements])
        except Exception as e:
            return Error(e)
    
    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            result = await self.page.evaluate(script, *args)
            return Ok(result)
        except Exception as e:
            return Error(e)
    
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Result[Optional[PlaywrightElementHandle], Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            try:
                element = await self.page.wait_for_selector(
                    selector, 
                    timeout=timeout or self.options.timeout
                )
                if element:
                    return Ok(PlaywrightElementHandle(element))
                return Ok(None)
            except Exception:
                # If selector times out, return None instead of raising an error
                return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def wait_for_navigation(self, timeout: Optional[int] = None) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.wait_for_load_state(
                "networkidle", 
                timeout=timeout or self.options.timeout
            )
            return Ok(None)
        except Exception as e:
            return Error(e)
            
    async def mouse_move(self, x: int, y: int) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.mouse.move(x, y)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def mouse_move_to_element(self, element: PlaywrightElementHandle, offset_x: int = 0, offset_y: int = 0) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            # Get element position
            bbox = await element.element.bounding_box()
            if not bbox:
                return Error(Exception("Failed to get element bounding box"))
                
            # Calculate center of element and add offset
            x = bbox["x"] + bbox["width"] / 2 + offset_x
            y = bbox["y"] + bbox["height"] / 2 + offset_y
            
            # Move to the calculated position
            await self.page.mouse.move(x, y)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def mouse_down(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.mouse.down(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def mouse_up(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.mouse.up(button=button)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def mouse_click(self, button: Literal["left", "right", "middle"] = "left", click_count: int = 1, delay_between_ms: Optional[int] = None) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            # Use Playwright's click method with options
            click_options: Dict[str, Any] = {
                "button": button,
                "click_count": click_count
            }
            
            if delay_between_ms is not None:
                click_options["delay"] = float(delay_between_ms)
                
            await self.page.mouse.click(0, 0, **click_options)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def mouse_double_click(self, button: Literal["left", "right", "middle"] = "left") -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            # Double click is just a click with click_count=2
            await self.page.mouse.click(0, 0, button=button, click_count=2)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def press(self, key: str) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.keyboard.press(key)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def key_down(self, key: str) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.keyboard.down(key)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def key_up(self, key: str) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            await self.page.keyboard.up(key)
            return Ok(None)
        except Exception as e:
            return Error(e)
    
    async def fill(self, text: str, delay: Optional[float] = None) -> Result[None, Exception]:
        try:
            if not self.page:
                return Error(Exception("Browser not launched"))
            
            options = {}
            if delay is not None:
                options["delay"] = delay
                
            await self.page.keyboard.type(text, **options)
            return Ok(None)
        except Exception as e:
            return Error(e)
