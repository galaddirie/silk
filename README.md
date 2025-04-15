# Silk

[![PyPI version](https://img.shields.io/badge/pypi-v0.2.5-blue.svg)](https://pypi.org/project/silk-scraper/)
[![Python versions](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/silk-scraper/)
[![codecov](https://codecov.io/gh/galaddirie/silk/graph/badge.svg?token=MFTEFWJ4EF)](https://codecov.io/gh/galaddirie/silk)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type check: mypy](https://img.shields.io/badge/type%20check-mypy-blue)](https://github.com/python/mypy)


**Silk** is a declative web scraping framework that transforms how you build web automation in Python. By leveraging composable "Actions", Silk enables you to craft elegant, resilient scrapers with true functional programming patterns. Built with [expression](https://github.com/dbrattli/Expression) and [fp-ops](https://github.com/galaddirie/fp-ops/)

## Key Features

- **Railway-Oriented Programming**: Honest error handling with errors as values.
- **Immutable Data Flow**: Thread-safe operations with predictable behavior
- **Resilient by Design**: Built-in retry mechanisms and fallback selectors
- **Browser Agnostic**: Unified API across Playwright, Selenium, and other automation tools
- **Parallelization**: Run operations concurrently with simple `&` composition

## First-Class Composition

Silk treats composition as a **first-class citizen**:

- **Actions as values**: Browser actions are composable units that can be stored, passed, and combined
- **Intuitive operators**: Compose with natural symbols (`>>`, `&`, `|`) for readable pipelines
- **Composition is associative**: (a >> b) >> c = a >> (b >> c) - allowing flexible pipeline construction
- **Modular architecture**: Complex workflows emerge from simple, reusable components

```python
# Silk's compositional approach
def get_product(url):
    return (
        Navigate(url)
        >> GetText(".product-title")
        >> GetText(".product-price")
    )

# Extract multiple items in parallel
def purchase_product():
    return (
        Query("#buy-button")
        >> Click
        >> Query("#checkout-button")
        >> Click
        >> GetText(".order-summary")
    )

# Compose the actions
purchase_flow = get_product >> purchase_product

# Execute the pipeline with a context
purchase_flow(context=context)
```

### Declarative API

Silk embraces **declarative programming** that focuses on **what** to accomplish, not **how**:

```python
# Imperative: HOW to perform login
driver.get(url)
driver.find_element_by_id("username").send_keys("user")
driver.find_element_by_id("password").send_keys("pass")
driver.page.mouse.move(
    driver.find_element_by_css_selector("button[type='submit']").rect["x"],
    driver.find_element_by_css_selector("button[type='submit']").rect["y"]
)
driver.page.mouse.down()
driver.page.mouse.up()

# Declarative: WHAT to accomplish with Silk
login_flow = (
    Navigate(url) 
    >> Fill("#username", "user") 
    >> Fill("#password", "pass") 
    >> Click("button[type='submit']")
)

# Execute the pipeline
login_flow("https://example.com/login")
```

With smart defaults silk allows you to write detectionless, declarative code that is easy to understand and maintain, without the need to worry about the underlying implementation details of the browser.

## Placeholder System

Silk provides a convenient placeholder system that simplifies function composition and lambda expressions:

```python
from silk.placeholder import _

add(1, 2) >> multiply(_, 2)

# is equivalent to
add(1, 2) >> (lambda x: multiply(x, 2))

add(1, 2).bind(lambda x: multiply(x, 2))
```

The `_` symbol acts as a placeholder for the value passed from the previous action, allowing for more concise and readable code when composing functions. This is especially useful in data transformation chains where the output of one action becomes the input to another.

### Examples

```python
from silk.placeholder import _
from silk.actions.elements import GetText
from silk.actions.navigation import Navigate

# Extract price and convert to float using placeholder
price_pipeline = (
    GetText(".price-element") 
    >> _.replace("$", "").strip() 
    >> float(_)
)

# Extract multiple data points and construct a dictionary
product_pipeline = (
    Navigate("https://example.com/product") 
    >> {
        "title": GetText(".product-title"),
        "price": GetText(".price") >> _.replace("$", "").strip() >> float(_),
        "rating": GetText(".rating") >> float(_)
    }
)
```

The placeholder system integrates seamlessly with Silk's compositional approach, enabling elegant data transformations without verbose lambda expressions.

## Installation

```bash
# Base installation
pip install silk-scraper

# With specific driver support
pip install silk-scraper[playwright]  # or [selenium], [puppeteer], [all]
```

## Quick Start

```python
import asyncio
from silk.actions.navigation import Navigate
from silk.actions.elements import GetText
from silk.browsers.manager import BrowserManager
from silk.actions.manage import InitializeContext

async def main():
    async with BrowserManager() as manager:
        # Create a context first
        context = await InitializeContext(manager)
        
        # Define a scraping pipeline
        pipeline = Navigate("https://example.com") >> GetText("h1")

        # Execute the pipeline
        result = await pipeline(context=context)

        if result.is_ok():
            print(f"Page title: {result.default_value(None)}")
        else:
            print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Actions

Actions are pure operations that form the building blocks of your scraping logic. Each Action:
- Takes an `ActionContext` as input
- Returns a `Result` containing either a value or an error
- Can be composed with other Actions using operators

### Composition Operators

- **`>>`** (then): Chain actions sequentially (Navigate to page, then extract element)
- **`&`** (and): Execute actions in parallel (Extract title and price simultaneously)
- **`|`** (or): Try one action, fall back to another if it fails (Try primary selector, fallback to alternative)

### Sequential Operations (`>>`)

```python
# Navigate to a page, then extract the title
Navigate(url) >> Click(title_selector)
```

### Parallel Operations (`&`)

```python
# Extract name, price, and description in parallel
# Each action is executed in a new context when using the & operator
Navigate(url) & Navigate(url2) & Navigate(url3)
```

```python
# Combining parallel and sequential operations
# Each parallel branch can contain its own chain of sequential actions
(
    # First website: Get product details
    (Navigate("https://site1.com/product")
     >> Wait(1000)
     >> GetText(".product-name"))
    &
    # Second website: Search and extract first result
    (Navigate("https://site2.com")
     >> Fill("#search-input", "smartphone")
     >> Click("#search-button")
     >> Wait(2000)
     >> GetText(".first-result .name"))
    &
    # Third website: Login and get account info
    (Navigate("https://site3.com/login")
     >> Fill("#username", "user@example.com")
     >> Fill("#password", "password123")
     >> Click(".login-button")
     >> Wait(1500)
     >> GetText(".account-info"))
)
# Results are collected as a Block of 3 items, one from each parallel branch
```

### Fallback Operations (`|`)

```python
# Try to extract with one selector, fall back to another if it fails
GetText(primary_selector) | GetText(fallback_selector)
```

Fallback operations are powerful tools for building resilient scraping pipelines. They allow you to try multiple scraping strategies and return the first successful result. in combination with SelectorGroups, you can create very robust scraping pipelines.

```python
from silk.actions.navigation import Navigate
from silk.actions.elements import GetText, GetAttribute, QueryAll, ExtractTable
from silk.actions.input import Click
from silk.flow import wait, retry
from silk.selectors.selector import SelectorGroup, css, xpath

# Example: Advanced product information scraping with multiple strategies
async def scrape_product(url, context):
    # Strategy 1: Direct extraction using primary selectors
    primary_strategy = (
        Navigate(url)
        >> GetText(".product-title")
    )

    # Strategy 2: Click on a tab first, then extract from revealed content
    secondary_strategy = (
        Navigate(url)
        >> Click(".details-tab")
        >> wait(500)  # Wait for tab content to load
        >> GetText(".tab-content h1")
    )

    # Strategy 3: Extract from structured JSON data in script tag
    json_strategy = (
        Navigate(url)
        >> GetAttribute('script[type="application/ld+json"]', "textContent")
        # Additional processing would parse the JSON and extract title
    )

    # Combine all strategies with fallback operator
    product_title_pipeline = (
        primary_strategy | secondary_strategy | json_strategy
    )

    # Multiple fallback approaches for price extraction
    price_pipeline = (
        # Try special sale price first
        (Navigate(url) >> GetText(".special-price .price-amount"))
        |
        # Then try regular price
        (Navigate(url) >> GetText(".regular-price"))
        |
        # Then try to extract from a pricing table
        (Navigate(url)
         >> ExtractTable("#pricing-table")
         # Additional processing would extract price from table data
        )
        |
        # Last resort: Try to find price in any element containing "$"
        (Navigate(url)
         >> QueryAll("*:contains('$')")
         # Additional processing would filter and extract price
        )
    )

    # Execute both pipelines
    title_result = await product_title_pipeline(context)
    price_result = await price_pipeline(context)

    return {
        "title": title_result.default_value("Unknown Title"),
        "price": price_result.default_value("Price Unavailable")
    }

# Example with SelectorGroups for even more resilience
def build_robust_product_scraper(url):
    # Create selector groups with multiple options
    title_selectors = SelectorGroup(
        "product_title",
        css(".product-title"),
        css("h1.title"),
        xpath("//div[@class='product-info']//h1"),
        css(".pdp-title")
    )

    price_selectors = SelectorGroup(
        "product_price",
        css(".special-price .amount"),
        css(".product-price"),
        xpath("//span[contains(@class, 'price')]"),
        css(".price-info .price")
    )

    image_selectors = SelectorGroup(
        "product_image",
        css(".product-image-gallery img"),
        css(".main-image"),
        xpath("//div[contains(@class, 'gallery')]//img")
    )

    # Use these groups in a pipeline with retries
    return (
        Navigate(url)
        >> retry(GetText(title_selectors), max_attempts=3, delay_ms=1000)
        >> retry(GetText(price_selectors), max_attempts=3, delay_ms=1000)
        >> retry(GetAttribute(image_selectors, "src"), max_attempts=3, delay_ms=1000)
    )
```

## Composition Functions

Silk provides a rich set of functions for composing actions that go beyond the basic operators. These functions enable powerful combinations of actions through clean, functional programming patterns. There is some overlap between symbol operators and these functions.

### sequence(*actions)

Combines multiple actions to execute in sequence, collecting **all** results into a Block.

```python
from silk.flow import sequence
from silk.actions.elements import GetText

# Extract multiple text elements in sequence
product_data = await sequence(
    GetText(".product-title"),
    GetText(".product-price"),
    GetText(".product-description")
)(context)

# product_data contains a Block with all three text values
titles = product_data.default_value(Block.empty())
```

### parallel(*actions)

Executes multiple actions in parallel and collects their results, improving performance for independent operations.

```python
from silk.flow import parallel
from silk.actions.navigation import Navigate
from silk.actions.elements import GetText

# Scrape multiple pages in parallel
results = await parallel(
    Navigate("https://site1.com") >> GetText(".data"),
    Navigate("https://site2.com") >> GetText(".data"),
    Navigate("https://site3.com") >> GetText(".data")
)(context)

# Each action runs in a separate browser context for true parallelism
```

### pipe(*actions)

Creates a pipeline where each action receives the result of the previous action, enabling data transformation chains.

```python
from silk.flow import pipe
from silk.actions.elements import GetText
from silk.actions.decorators import action
from expression import Ok, Error

@action
async def parse_price(context, price_text):
    # Convert "$42.99" to a float
    try:
        price = float(price_text.replace('$', '').strip())
        return Ok(price)
    except ValueError:
        return Error(f"Failed to parse price from: {price_text}")

# Extract text and transform it
price = await pipe(
    GetText(".price"),        # Returns "$42.99"
    lambda text: parse_price(text)  # Transforms to 42.99
)(context)
```

### fallback(*actions)

Tries actions in sequence until one succeeds. This is the functional equivalent of the `|` operator.

```python
from silk.flow import fallback
from silk.actions.elements import GetText

# Try multiple selectors for price
price = await fallback(
    GetText(".sale-price"),
    GetText(".regular-price"),
    GetText(".price")
)(context)

# Returns the first successful extraction
```

### compose(*actions)

Composes actions to execute in sequence, similar to the `>>` operator, but returns only the last result.

```python
from silk.flow import compose
from silk.actions.navigation import Navigate
from silk.actions.input import Click
from silk.actions.elements import GetText

# Navigate, click, and extract data
product_name = await compose(
    Navigate(url),
    Click(".product-link"),
    GetText(".product-title")  # Only this result is returned
)(context)
```

## Flow Control Functions

Silk provides robust flow control functions that enable complex scraping logic with minimal code.

### branch(condition, if_true, if_false)

Conditionally executes different actions based on a condition, similar to an if-else statement.

```python
from silk.flow import branch
from silk.actions.elements import GetText, ElementExists

# Check if an element exists and take different actions
result = await branch(
    ElementExists(".out-of-stock"),
    GetText(".out-of-stock-message"),  # If out of stock
    GetText(".in-stock-price")         # If in stock
)(context)
```

### loop_until(condition, body, max_iterations, delay_ms)

Repeatedly executes an action until a condition is met or max iterations reached.

```python
from silk.flow import loop_until
from silk.actions.input import Click
from silk.actions.elements import ElementExists, GetText

# Click "Load More" until a specific product appears
product_details = await loop_until(
    ElementExists("#target-product"),
    Click("#load-more-button"),
    max_iterations=10,
    delay_ms=1000
)(context)

# After finding the element, extract its details
product_name = await GetText("#target-product .name")(context)
```

### retry(action, max_attempts, delay_ms)

Retries an action until it succeeds or reaches maximum attempts, perfect for handling intermittent failures.

```python
from silk.flow import retry
from silk.actions.elements import GetText

# Retry text extraction up to 3 times
price = await retry(
    GetText("#dynamic-price"),
    max_attempts=3,
    delay_ms=1000
)(context)
```

### retry_with_backoff(action, max_attempts, initial_delay_ms, backoff_factor, jitter)

Implements exponential backoff for retries, reducing server load and improving success rates.

```python
from silk.flow import retry_with_backoff
from silk.actions.navigation import Navigate

# Retry with exponential backoff and jitter
page = await retry_with_backoff(
    Navigate("https://example.com/product"),
    max_attempts=5,
    initial_delay_ms=1000,
    backoff_factor=2.0,  # Each retry doubles the wait time
    jitter=True          # Adds randomness to prevent request clustering
)(context)
```

### with_timeout(action, timeout_ms)

Executes an action with a timeout constraint, preventing operations from hanging indefinitely.

```python
from silk.flow import with_timeout
from silk.actions.elements import GetText

# Set a 5-second timeout for extraction
try:
    result = await with_timeout(
        GetText("#slow-loading-element"),
        timeout_ms=5000
    )(context)
except Exception as e:
    print(f"Extraction timed out: {e}")
```

### tap(main_action, side_effect)

Executes a main action and a side effect action, returning only the main result.

```python
from silk.flow import tap, log
from silk.actions.elements import GetText

# Extract text and log it without affecting the pipeline
product_name = await tap(
    GetText(".product-title"),
    log("Product title extracted successfully")
)(context)
```

### wait(ms)

Creates a simple delay in the action pipeline, useful for waiting for page elements to load.

```python
from silk.flow import wait
from silk.actions.navigation import Navigate
from silk.actions.elements import GetText

# Navigate, wait for content to load, then extract
title = await (
    Navigate("https://example.com")
    >> wait(2000)  # Wait 2 seconds for page to fully load
    >> GetText("h1")
)(context)
```

## Real-World Example

```python
# Define reusable extraction component
extract_product_data = (
    GetText(".product-title") &
    GetText(".product-price") &
    GetAttribute(".product-image", "src") &
    GetText(".stock-status")
)

# Complete scraping pipeline with error handling and resilience
product_scraper = (
    Navigate(product_url)
    >> wait(1000)  # Wait for dynamic content
    >> extract_product_data
    >> ParseProductData()  # Custom transformation
).with_retry(max_attempts=3, delay_ms=1000)

# Scale to multiple products effortlessly
scrape_multiple_products = parallel(*(
    product_scraper(url) for url in product_urls
))

# Execute with context
results = await scrape_multiple_products(context)
```

## Creating Custom Actions

Extend Silk with your own custom actions:

```python
from silk.actions.decorators import action
from expression import Ok, Error

@action
async def extract_price(context, selector):
    """Extract and parse a price from the page"""
    page_result = await context.get_page()
    if page_result.is_error():
        return page_result

    page = page_result.default_value(None)
    if page is None:
        return Error("No page found")

    # Extract text from element
    text_result = await (
        page.query_selector(selector)
        .then(lambda elem: elem.get_text())
    )

    if text_result.is_error():
        return text_result

    text = text_result.default_value(None)

    try:
        # Parse price from text
        price = float(text.replace('$', '').strip())
        return Ok(price)
    except ValueError:
        return Error(f"Failed to parse price from: {text}")
```

## Browser Configuration

```python
from silk.browsers.types import BrowserOptions
from silk.browsers.manager import BrowserManager
from silk.actions.manage import InitializeContext

options = BrowserOptions(
    headless=False,  # Show browser UI for debugging
    browser_name="chromium",
    viewport={"width": 1280, "height": 800}
)

manager = BrowserManager(driver_type="playwright", default_options=options)
context = await InitializeContext(manager)
```

---

## API Reference

### Module Structure

```
silk/
├── actions/         # Core actions for browser interaction
│   ├── context.py   # Action context definitions
│   ├── decorators.py # Action decorators
│   ├── elements.py  # Element interaction (GetText, GetAttribute, etc.)
│   ├── input.py     # User input simulation (Click, Fill, etc.)
│   ├── manage.py    # Context management (InitializeContext, WithContext)
│   └── navigation.py # Page navigation actions
├── browsers/        # Browser drivers and management
│   ├── manager.py   # BrowserManager for session handling
│   └── types.py     # Browser configuration types
├── flow/            # Flow control and composition utilities
│   ├── branch.py    # Conditional execution
│   ├── loop.py      # Iteration control
│   ├── parallel.py  # Concurrent execution
│   ├── retry.py     # Retry mechanisms
│   └── sequence.py  # Sequential composition
├── placeholder.py   # Placeholder system for composition
└── selectors/       # Selector definitions and utilities
    └── selector.py  # Selector types and groups
```

### Core Actions

#### Navigation Actions
- `Navigate(url: str)` - Navigate to a URL
- `Reload()` - Reload the current page
- `Back()` - Navigate back in history
- `Forward()` - Navigate forward in history
- `WaitForSelector(selector)` - Wait for a selector to appear
- `Screenshot(path: str)` - Take a screenshot of the page

#### Element Actions
- `GetText(selector)` - Extract text from an element
- `GetAttribute(selector, attribute: str)` - Get an attribute value
- `Query(selector)` - Find a single element
- `QueryAll(selector)` - Find all matching elements
- `ElementExists(selector)` - Check if an element exists
- `ExtractTable(selector)` - Extract data from an HTML table

#### Input Actions
- `Click(selector)` - Click an element
- `Fill(selector, value: str)` - Fill a form field
- `Type(selector, text: str)` - Type text into an element
- `Press(selector, key: str)` - Press a key on an element
- `Hover(selector)` - Hover over an element
- `Select(selector, value: str)` - Select an option from a dropdown

#### Context Management
- `InitializeContext(browser_manager)` - Create a new context
- `WithContext(context_factory, action)` - Execute an action with a specific context

### Flow Control Functions

#### Composition
- `sequence(*actions)` - Execute actions in sequence, returning all results
- `parallel(*actions)` - Execute actions in parallel, returning all results
- `pipe(*actions)` - Chain actions, passing each result to the next action
- `compose(*actions)` - Compose actions sequentially, returning only the last result
- `fallback(*actions)` - Try actions in sequence until one succeeds

#### Control Flow
- `branch(condition, if_true, if_false)` - Conditional execution based on a condition
- `loop_until(condition, body, max_iterations, delay_ms)` - Repeat an action until a condition is met
- `retry(action, max_attempts, delay_ms)` - Retry an action multiple times
- `retry_with_backoff(action, max_attempts, initial_delay_ms, backoff_factor, jitter)` - Retry with exponential backoff
- `with_timeout(action, timeout_ms)` - Execute an action with a timeout
- `tap(main_action, side_effect)` - Execute an action with a side effect
- `wait(ms)` - Pause execution for a specified time

### Selectors

#### Selector Types
- `css(selector: str)` - Create a CSS selector
- `xpath(selector: str)` - Create an XPath selector
- `text(content: str)` - Create a text content selector

#### Selector Groups
- `SelectorGroup(name: str, *selectors)` - Create a group of selectors with fallbacks

### Browser Management

#### Configuration
- `BrowserOptions` - Browser configuration options (headless, viewport, etc.)
- `NavigationOptions` - Page navigation options (timeout, wait_until, etc.)

#### Browser Manager
- `BrowserManager(driver_type: str, default_options: BrowserOptions)` - Manage browser sessions

---

## Roadmap

- [x] Initial release with Playwright support
- [ ] Improve parallel execution
- [ ] Support multiple actions in parallel in the same context/page eg. (GetText & GetAttribute & GetHtml) in an ergonomic way
- [ ] Implement left shift (<<) operator for context modifiers and action decorators
- [ ] improve manager ergonomics
- [ ] Selenium integration
- [ ] Puppeteer integration
- [ ] Add examples
- [ ] Support Mapped tasks similar to airflow tasks eg. (QueryAll >> GetText[]) where get text is applied to each element in the collection
- [ ] Add proxy options
- [ ] Explore stealth options for browser automation ( implement patchwright, no-driver, driverless, etc.)
- [ ] add dependency review
- [ ] Support for task dependencies
- [ ] action signature validation
- [ ] Data extraction DSL for declarative scraping
- [ ] Support computer using agentds (browser-use, openai cua, claude computer-use)
- [ ] Enhanced caching mechanisms
- [ ] Distributed scraping support
- [ ] Rate limiting and polite scraping utilities
- [ ] Integration with popular data processing libraries (Pandas, etc.)
- [ ] CLI tool for quick scraping tasks
