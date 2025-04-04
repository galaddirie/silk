from typing import Optional, List, Any, Dict, cast
from pathlib import Path
import asyncio
from patchright.async_api import async_playwright, Browser, Page, ElementHandle as PlaywrightElement

from silk.browser.driver import BrowserDriver, BrowserOptions, ElementHandle


class PlaywrightElementHandle(ElementHandle):
    """Implementation of ElementHandle for Playwright"""
    
    def __init__(self, element: PlaywrightElement):
        self.element = element
    
    async def click(self) -> None:
        await self.element.click()
    
    async def type(self, text: str) -> None:
        await self.element.type(text)
    
    async def get_text(self) -> str:
        return await self.element.text_content() or ""
    
    async def get_attribute(self, name: str) -> Optional[str]:
        return await self.element.get_attribute(name)
    
    async def is_visible(self) -> bool:
        return await self.element.is_visible()


class PlaywrightDriver(BrowserDriver[PlaywrightElementHandle]):
    """Implementation of BrowserDriver using Playwright"""
    
    def __init__(self, options: BrowserOptions):
        super().__init__(options)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def launch(self) -> None:
        self.playwright = await async_playwright().start()
        
        # Configure browser launch options
        browser_type = self.playwright.chromium
        launch_options = {
            "headless": self.options.headless
        }
        
        if self.options.proxy:
            launch_options["proxy"] = {"server": self.options.proxy}
        
        # Add extra arguments if any
        if self.options.extra_args:
            launch_options.update(self.options.extra_args)
        
        self.browser = await browser_type.launch(**launch_options)
        self.page = await self.browser.new_page()
        
        # Configure page
        await self.page.set_viewport_size({
            "width": self.options.viewport_width,
            "height": self.options.viewport_height
        })
        
        if self.options.user_agent:
            await self.page.set_extra_http_headers({"User-Agent": self.options.user_agent})
        
        # Set cookies if any
        if self.options.cookies:
            await self.page.context.add_cookies(self.options.cookies)
        
        # Set default timeout
        self.page.set_default_timeout(self.options.timeout)
    
    async def close(self) -> None:
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
    
    async def goto(self, url: str) -> None:
        if not self.page:
            raise Exception("Browser not launched")
        
        await self.page.goto(url, wait_until="networkidle")
    
    async def current_url(self) -> str:
        if not self.page:
            raise Exception("Browser not launched")
        
        return self.page.url
    
    async def get_page_source(self) -> str:
        if not self.page:
            raise Exception("Browser not launched")
        
        return await self.page.content()
    
    async def take_screenshot(self, path: Path) -> None:
        if not self.page:
            raise Exception("Browser not launched")
        
        await self.page.screenshot(path=str(path))
    
    async def query_selector(self, selector: str) -> Optional[PlaywrightElementHandle]:
        if not self.page:
            raise Exception("Browser not launched")
        
        element = await self.page.query_selector(selector)
        if element:
            return PlaywrightElementHandle(element)
        return None
    
    async def query_selector_all(self, selector: str) -> List[PlaywrightElementHandle]:
        if not self.page:
            raise Exception("Browser not launched")
        
        elements = await self.page.query_selector_all(selector)
        return [PlaywrightElementHandle(element) for element in elements]
    
    async def execute_script(self, script: str, *args: Any) -> Any:
        if not self.page:
            raise Exception("Browser not launched")
        
        return await self.page.evaluate(script, *args)
    
    async def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> Optional[PlaywrightElementHandle]:
        if not self.page:
            raise Exception("Browser not launched")
        
        try:
            element = await self.page.wait_for_selector(
                selector, 
                timeout=timeout or self.options.timeout
            )
            if element:
                return PlaywrightElementHandle(element)
        except:
            pass
        
        return None
    
    async def wait_for_navigation(self, timeout: Optional[int] = None) -> None:
        if not self.page:
            raise Exception("Browser not launched")
        
        await self.page.wait_for_load_state(
            "networkidle", 
            timeout=timeout or self.options.timeout
        )
