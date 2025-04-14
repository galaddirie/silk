import asyncio
import time
from pathlib import Path

from expression.core import Error, Ok, Result

from silk.actions.context import ActionContext
from silk.actions.navigation import Navigate, WaitForSelector, Screenshot
from silk.actions.elements import GetText, GetAttribute, Query, QueryAll, ExtractTable
from silk.actions.input import Click, Fill
from silk.flow import retry, wait
from silk.primitives import constant
from silk.actions.manage import (
     WithContext,
     InitializeContext
)
from silk.selectors.selector import SelectorGroup, Selector, css
from silk.browsers.manager import BrowserManager
from silk.browsers.types import BrowserOptions, NavigationOptions

async def test_book_catalog_extraction():
    """Test a basic book catalog extraction pipeline from books.toscrape.com."""
    # Create real browser manager with Playwright
    async with BrowserManager(driver_type="playwright", default_options=BrowserOptions(headless=False)) as browser_manager:


        
        # currently navigation opens  but break 
        # Navigated to https://books.toscrape.com/
        # Error Operation QueryAll requires a context, but none was provided
        context = await InitializeContext(browser_manager)
        pipeline = (
            Navigate("https://books.toscrape.com/" ) 
            >> QueryAll(css(".product_pod"))
            .map(lambda elements: elements[:5])
        )

        
        # Execute the pipeline
        result = await pipeline(context=context)
        
        print(result)

        if result.is_error():
            print(result.error)
        else:
            print(result.default_value([]))


asyncio.run(test_book_catalog_extraction())
