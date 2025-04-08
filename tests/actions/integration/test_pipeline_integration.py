import asyncio
import pytest
from typing import List, Dict, Any, Optional
import os
import logging

from expression.core import Result, Ok, Error
from expression.collections import Block

from silk.browsers.manager import BrowserManager
from silk.models.browser import BrowserOptions, ActionContext
from silk.actions.navigation import Navigate
from silk.actions.extraction import GetText, GetAttribute, GetHtml, QueryAll
from silk.actions.input import Click, Fill, Select, MouseMove
from silk.actions.flow import branch, loop_until, retry, retry_with_backoff, wait, tap, log as log_action
from silk.actions.composition import sequence, parallel, pipe, fallback, compose
from silk.selectors.selector import SelectorGroup, Selector, SelectorType, css, xpath
from silk.actions.base import Action
from silk.actions.decorators import action

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("silk_e2e_test")

# Base URL for our E2E tests
BASE_URL = "http://books.toscrape.com"

@action()
async def extract_book_data(context: ActionContext, data_block: Block[Any]) -> Result[Dict[str, Any], Exception]:
    """Custom action to parse extracted book data into a structured format"""
    try:
        if len(data_block) < 4:
            return Error(Exception(f"Insufficient data in block, expected 4 elements, got {len(data_block)}"))
            
        # Extract data from block
        # First item is title, second is price, third is availability, fourth is rating
        book = {
            "title": data_block[0].strip() if data_block[0] else "Unknown title",
            "price": data_block[1].strip() if data_block[1] else "Unknown price",
            "availability": data_block[2].strip() if data_block[2] else "Unknown availability",
            "rating": data_block[3] if data_block[3] else "Unknown rating"
        }
        return Ok(book)
    except Exception as e:
        return Error(e)

@action()
async def extract_category_links(context: ActionContext, html_content: str) -> Result[List[str], Exception]:
    """Extract category links from the side navigation"""
    try:
        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)
            
        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("Failed to get page"))
            
        # Use JavaScript to extract links from the side navigation
        result = await page.execute_script("""
            const links = Array.from(document.querySelectorAll('.side_categories ul li a'));
            return links.map(link => link.getAttribute('href'));
        """)
        
        if result.is_error():
            return Error(result.error)
            
        links = result.default_value([])
        # Filter out None values and convert relative links to absolute
        absolute_links = [f"{BASE_URL}/{link.lstrip('/')}" for link in links if link]
        return Ok(absolute_links)
    except Exception as e:
        return Error(e)

@action()
async def extract_book_links(context: ActionContext, html_content: str) -> Result[List[str], Exception]:
    """Extract book links from a category page"""
    try:
        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)
            
        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("Failed to get page"))
            
        # Use JavaScript to extract links from the book list
        result = await page.execute_script("""
            const books = Array.from(document.querySelectorAll('.product_pod h3 a'));
            return books.map(book => book.getAttribute('href'));
        """)
        
        if result.is_error():
            return Error(result.error)
            
        links = result.default_value([])
        # Convert relative links to absolute
        base_url = page.url
        absolute_links = []
        for link in links:
            if link:
                if '/' in link:
                    # Convert "../../../" paths to absolute URLs
                    parts = base_url.split('/')
                    back_count = link.count('../')
                    
                    # Remove the appropriate number of parts
                    parts = parts[:-back_count-1] if back_count > 0 else parts
                    
                    # Add the actual path part after removing "../" prefixes
                    clean_link = link.replace('../', '')
                    absolute_links.append('/'.join(parts) + '/' + clean_link)
                else:
                    absolute_links.append(f"{base_url}/{link}")
                    
        return Ok(absolute_links)
    except Exception as e:
        return Error(e)

@action()
async def parse_rating(context: ActionContext, element_class: Optional[str]) -> Result[str, Exception]:
    """Parse the star rating from class name"""
    try:
        if not element_class:
            return Ok("No rating")
            
        # Classes are like "star-rating Three" or "star-rating One"
        rating_map = {
            "One": "1 star",
            "Two": "2 stars",
            "Three": "3 stars", 
            "Four": "4 stars",
            "Five": "5 stars"
        }
        
        for rating_text, rating_value in rating_map.items():
            if rating_text in element_class:
                return Ok(rating_value)
                
        return Ok("Unknown rating")
    except Exception as e:
        return Error(e)


class TestE2EPipelineIntegration:
    @pytest.mark.asyncio
    async def test_basic_navigation_and_extraction(self):
        """Test basic navigation and extraction pipeline"""
        # Define browser options
        options = BrowserOptions(
            headless=True,
            browser_name="chromium",
            viewport={"width": 1280, "height": 800}
        )
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Define a simple pipeline to navigate and extract the title
            pipeline = Navigate(BASE_URL) >> GetText("h1")
            
            # Execute the pipeline
            result = await pipeline(manager)
            
            # Verify results
            assert result.is_ok()
            assert "Books to Scrape" in result.default_value("")
    
    @pytest.mark.asyncio
    async def test_category_navigation(self):
        """Test navigating to a category and extracting books"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Navigate to a specific category (Travel)
            pipeline = (
                Navigate(f"{BASE_URL}/catalogue/category/books/travel_2/index.html")
                >> GetText("h1")
            )
            
            result = await pipeline(manager)
            assert result.is_ok()
            assert "Travel" in result.default_value("")
            
            # Now extract all book titles in this category
            book_titles_pipeline = (
                Navigate(f"{BASE_URL}/catalogue/category/books/travel_2/index.html")
                >> QueryAll(".product_pod h3 a")
                >> sequence(*[GetText(f"[data-index='{i}']") for i in range(20)])
            )
            
            titles_result = await book_titles_pipeline(manager)
            assert titles_result.is_ok()
            
            titles = titles_result.default_value(Block.empty())
            assert len(titles) > 0, "Should find some book titles"
            
            logger.info(f"Found {len(titles)} travel books, first few: {titles[:3]}")
    
    @pytest.mark.asyncio
    async def test_search_and_filter(self):
        """Test searching and filtering functionality"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Since the site doesn't have a search form, we'll simulate filtering
            # by navigating to a category and then filtering by price
            
            # First navigate to fiction category
            fiction_url = f"{BASE_URL}/catalogue/category/books/fiction_10/index.html"
            
            # Define selectors for extracting inexpensive books (< £20)
            inexpensive_books_pipeline = (
                Navigate(fiction_url)
                >> wait(500)  # Wait for page to load
                >> parallel(
                    QueryAll(".product_pod"),  # All books
                    QueryAll(".product_pod .price_color")  # All prices
                )
                >> sequence(*[
                    compose(
                        GetText(f".product_pod:nth-child({i}) .price_color"),
                        # Checking if it's inexpensive using a lambda function here
                        lambda price: branch(
                            # Condition: price < £20
                            action()(lambda ctx, p: Ok(float(p.replace('£', '')) < 20)),
                            # If true, get the title
                            GetText(f".product_pod:nth-child({i}) h3 a"),
                            # If false, return empty string
                            action()(lambda ctx, _: Ok(""))
                        )
                    ) for i in range(1, 21)  # Loop through first 20 books
                ])
            )
            
            result = await inexpensive_books_pipeline(manager)
            assert result.is_ok()
            
            # Filter out empty strings
            inexpensive_books = [book for book in result.default_value(Block.empty()) if book]
            
            assert len(inexpensive_books) > 0, "Should find some inexpensive books"
            logger.info(f"Found {len(inexpensive_books)} inexpensive fiction books")
    
    @pytest.mark.asyncio
    async def test_detailed_book_extraction(self):
        """Test extracting detailed information about a book"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Navigate to a specific book
            book_url = f"{BASE_URL}/catalogue/its-only-the-himalayas_981/index.html"
            
            # Define selectors for different book data
            title_selectors = SelectorGroup(
                "book_title",
                css("h1"),
                xpath("//h1"),
                css(".product_main h1")
            )
            
            price_selectors = SelectorGroup(
                "book_price",
                css(".price_color"),
                xpath("//p[@class='price_color']"),
                css(".product_main .price_color")
            )
            
            availability_selectors = SelectorGroup(
                "book_availability", 
                css(".availability"),
                xpath("//p[@class='availability']"),
                css(".product_main .availability")
            )
            
            # Create custom action to get rating
            get_rating = compose(
                GetAttribute(".star-rating", "class"),
                parse_rating
            )
            
            # Define pipeline to extract book details with fallbacks
            book_details_pipeline = (
                Navigate(book_url)
                >> wait(500)  # Wait for page to load completely
                >> parallel(
                    retry(GetText(title_selectors), max_attempts=3),
                    retry(GetText(price_selectors), max_attempts=3),
                    retry(GetText(availability_selectors), max_attempts=3),
                    retry(get_rating, max_attempts=3)
                )
                >> extract_book_data
            )
            
            result = await book_details_pipeline(manager)
            assert result.is_ok()
            
            book_data = result.default_value({})
            assert book_data["title"] == "It's Only the Himalayas"
            assert "£" in book_data["price"]
            assert "availability" in book_data
            assert "rating" in book_data
            
            logger.info(f"Book details: {book_data}")
    
    @pytest.mark.asyncio
    async def test_pagination(self):
        """Test pagination by navigating through multiple pages"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Start at page 1 of all books
            start_url = f"{BASE_URL}/catalogue/page-1.html"
            
            # Create a pipeline that extracts books from current page and navigates to next page
            books_from_first_pages = []
            
            # Navigate to first page
            navigate_result = await Navigate(start_url)(manager)
            assert navigate_result.is_ok()
            
            # Create a context for following actions
            context_result = await manager.create_context(nickname="pagination_test")
            assert context_result.is_ok()
            browser_context = context_result.default_value(None)
            assert browser_context is not None
            
            action_context = ActionContext(
                browser_manager=manager,
                context_id=browser_context.id,
                page_id=list(browser_context.pages.keys())[0] if browser_context.pages else None
            )
            
            # Extract books from the first 3 pages
            for page_num in range(1, 4):
                # Get all book titles on current page
                titles_pipeline = QueryAll(".product_pod h3 a") >> sequence(*[
                    GetText(f"[data-index='{i}']") for i in range(20)
                ])
                
                titles_result = await titles_pipeline(action_context)
                assert titles_result.is_ok()
                
                page_titles = [t for t in titles_result.default_value(Block.empty()) if t]
                books_from_first_pages.extend(page_titles)
                
                logger.info(f"Page {page_num}: Found {len(page_titles)} books")
                
                # If not last page, navigate to next page
                if page_num < 3:
                    next_page_url = f"{BASE_URL}/catalogue/page-{page_num + 1}.html"
                    next_result = await Navigate(next_page_url)(action_context)
                    assert next_result.is_ok()
            
            # Verify we collected books from multiple pages
            assert len(books_from_first_pages) > 40, "Should find at least 40 books across 3 pages"
            
            # Clean up
            await manager.close_context(browser_context.id)
    
    @pytest.mark.asyncio
    async def test_complex_workflow(self):
        """Test a complex scraping workflow that simulates a real-world scenario"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Create a workflow that:
            # 1. Extracts category links
            # 2. Navigates to a random category (we'll use Science)
            # 3. Extracts book links from that category
            # 4. Gets detailed info about the first book
            
            # Step 1: Navigate to homepage and extract categories
            get_categories_pipeline = (
                Navigate(BASE_URL)
                >> GetHtml(".side_categories")
                >> extract_category_links
            )
            
            categories_result = await get_categories_pipeline(manager)
            assert categories_result.is_ok()
            
            categories = categories_result.default_value([])
            assert len(categories) > 0, "Should find some categories"
            
            # Find the Science category link
            science_url = None
            for url in categories:
                if "/science_22/" in url:
                    science_url = url
                    break
            
            assert science_url is not None, "Science category should exist"
            
            # Step 2: Navigate to Science category and extract book links
            get_books_pipeline = (
                Navigate(science_url)
                >> GetHtml(".products-container")
                >> extract_book_links
            )
            
            books_result = await get_books_pipeline(manager)
            assert books_result.is_ok()
            
            book_links = books_result.default_value([])
            assert len(book_links) > 0, "Should find some book links"
            
            # Step 3: Get detailed info about the first book
            if book_links:
                first_book_url = book_links[0]
                
                # Define reusable extraction pipeline for book details
                extract_book_details = parallel(
                    GetText(".product_main h1"),
                    GetText(".price_color"),
                    GetText(".availability"),
                    compose(
                        GetAttribute(".star-rating", "class"),
                        parse_rating
                    )
                )
                
                # Complete pipeline with error handling and logging
                book_pipeline = (
                    Navigate(first_book_url)
                    >> wait(500)
                    >> tap(
                        extract_book_details >> extract_book_data,
                        log_action("Book data extraction completed")
                    )
                )
                
                book_result = await book_pipeline(manager)
                assert book_result.is_ok()
                
                book = book_result.default_value({})
                assert "title" in book
                assert "price" in book
                assert "availability" in book
                assert "rating" in book
                
                logger.info(f"Successfully extracted science book details: {book}")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery with Railway-Oriented Programming"""
        options = BrowserOptions(headless=True)
        
        async with BrowserManager(driver_type="playwright", default_options=options) as manager:
            # Test fallback when trying to access non-existent page
            non_existent_url = f"{BASE_URL}/non-existent-page.html"
            
            fallback_pipeline = fallback(
                Navigate(non_existent_url) >> GetText("h1"),
                Navigate(BASE_URL) >> GetText("h1")
            )
            
            result = await fallback_pipeline(manager)
            assert result.is_ok()
            assert "Books to Scrape" in result.default_value("")
            
            # Test retrying an intermittently available element
            # We'll simulate this by trying to get an element that doesn't exist,
            # then falling back to one that does
            retry_pipeline = (
                Navigate(BASE_URL)
                >> retry_with_backoff(
                    GetText(".element-that-doesnt-exist"),
                    max_attempts=2,
                    initial_delay_ms=500,
                    backoff_factor=2.0
                ) | GetText("h1")  # Fallback if retry fails
            )
            
            retry_result = await retry_pipeline(manager)
            assert retry_result.is_ok()
            assert "Books to Scrape" in retry_result.default_value("")
            
            @action()
            async def element_exists(context: ActionContext, selector: str) -> Result[bool, Exception]:
                """Check if an element exists on the page"""
                page_result = await context.get_page()
                if page_result.is_error():
                    return Error(page_result.error)
                page = page_result.default_value(None)
                if page is None:
                    return Error(Exception("Failed to get page"))
                return Ok(await page.wait_for_selector(selector))
            
            # Test branching based on element existence
            branching_pipeline = (
                Navigate(BASE_URL)
                >> branch(
                    element_exists(".side_categories h3"),                    
                    GetText(".side_categories h3"),     # If true
                    GetText("h1")                       # If false
                )
            )
            
            branch_result = await branching_pipeline(manager)
            assert branch_result.is_ok()
            assert "Books" in branch_result.default_value("")


if __name__ == "__main__":
    # Run the tests manually if needed
    asyncio.run(TestE2EPipelineIntegration().test_basic_navigation_and_extraction())