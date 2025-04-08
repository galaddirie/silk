# Silk

[![PyPI version](https://img.shields.io/badge/pypi-v0.1.1-blue.svg)](https://pypi.org/project/silk-scraper/)
[![Python versions](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/silk-scraper/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type check: mypy](https://img.shields.io/badge/type%20check-mypy-blue)](https://github.com/python/mypy)

**Silk** is a functional web scraping framework for Python that reimagines how web automation should work. Built around composable "Actions" and the [Expression](https://github.com/dbrattli/Expression) library, Silk enables you to write elegant, maintainable, and resilient web scrapers with true functional programming patterns.

Unlike traditional scraping libraries, Silk embraces Railway-Oriented Programming for robust error handling, uses immutable data structures for predictability, and provides an expressive, composable API that makes even complex scraping workflows readable and maintainable.

## Why Silk?

Traditional web scraping approaches in Python often lead to complex, brittle code that's difficult to maintain. Silk solves these common challenges:
- **Declarative**: Express your scraping goals directly without implementation details
- **No More Callback Hell**: Replace nested try/except blocks with elegant Railway-Oriented Programming
- **Resilient Scraping**: Built-in retry mechanisms, fallback selectors, and error recovery
- **Composable Actions**: Chain operations with intuitive operators (`>>`, `&`, `|`) for cleaner code
- **Type-Safe**: Full typing support with Mypy and Pydantic for fewer runtime errors
- **Browser Agnostic**: Same API for Playwright, Selenium, or any other browser automation tool
- **Parallelization Made Easy**: Run operations concurrently with the `&` operator

Whether you're building a small data collection script or a large-scale scraping system, Silk's functional approach scales with your needs while keeping your codebase clean and maintainable.

## Composition as a First-Class Citizen

At the heart of Silk lies the fundamental principle that **composition is a first-class citizen**, not just an add-on feature. This means:

- **Actions are values**: Every operation is a composable unit that can be stored, passed around, and combined
- **Expressive operators**: Intuitive symbols (`>>`, `&`, `|`) make composition feel natural and readable, 
- **Pipeline-oriented thinking**: Build complex workflows by combining simpler operations
- **Mix and match**: Compose any actions together regardless of their implementation details

Compare the traditional approach:

```python
# Traditional approach with nested logic and state management
try:
    driver.get(url)
    try:
        element = driver.find_element_by_css_selector(".product-title")
        product_title = element.text
        try:
            price_element = driver.find_element_by_css_selector(".product-price")
            product_price = price_element.text
            # ... more nested code ...
        except:
            # Error handling for price
    except:
        # Error handling for title
except:
    # Error handling for navigation
```

With Silk's compositional approach:

```python
# Silk's compositional approach
product_info = (
    Navigate(url)
    >> GetText(".product-title")  # This operation uses the result of Navigate
    >> GetText(".product-price")   # This operation uses the result of the previous GetText
)

# Or extract multiple items in parallel
product_details = Navigate(url) >> (
    GetText(".product-title") & 
    GetText(".product-price") & 
    GetAttribute(".product-image", "src")
)
```

## Declarative API: Describe What, Not How

Silk embraces a declarative programming model that lets you focus on **what** you want to accomplish rather than **how** to do it:

- **Intent-focused**: Express your scraping goals directly without implementation details
- **Separation of concerns**: Define what data to extract separately from how to handle errors or retries
- **Higher level of abstraction**: Work with scraping concepts rather than browser automation primitives
- **Self-documenting code**: Code that reads like a description of the scraping process

Compare an imperative approach:

```python
# Imperative: HOW to do things
driver.get(url)
driver.find_element_by_id("username").send_keys("user")
driver.find_element_by_id("password").send_keys("pass")
driver.find_element_by_css_selector("button[type='submit']").click()

# Declarative: WHAT to do (with Silk)
login_flow = (
    Navigate(url)
    >> Fill("#username", "user") 
    >> Fill("#password", "pass")
    >> Click("button[type='submit']")
)
```

## Features

- **Purely Functional Design**: Built on Expression library for robust functional programming in Python
- **Immutable Data Structures**: Uses immutable collections for thread-safety and predictability
- **Railway-Oriented Programming**: Elegant error handling with Result types
- **Functional & Composable API**: Build pipelines with intuitive operators (`>>`, `&`, `|`)
- **Browser Abstraction**: Works with Playwright, Selenium, or any other browser automation tool
- **Resilient Selectors**: Fallback mechanisms to handle changing website structures
- **Type Safety**: Leverages Pydantic, Mypy and Python's type hints for static type checking
- **Parallel Execution**: Easy concurrent scraping with functional composition

## Installation

You can install Silk with your preferred browser driver:

```bash
# Base installation (no drivers)
pip install silk-scraper

# With Playwright support
pip install silk-scraper[playwright]

# With Selenium support
pip install silk-scraper[selenium]

# With Puppeteer support
pip install silk-scraper[puppeteer]

# With all drivers
pip install silk-scraper[all]
```

## Quick Start

### Basic Example

Here's a minimal example to get you started with Silk:

```python
import asyncio
from silk.actions.navigation import Navigate
from silk.actions.extraction import GetText
from silk.browsers.manager import BrowserManager

async def main():
    # Create a browser manager (defaults to Playwright)
    async with BrowserManager() as manager:
        # Define a simple scraping pipeline
        pipeline = (
            Navigate("https://example.com") 
            >> GetText("h1")
        )
        
        # Execute the pipeline
        result = await pipeline(manager)
        
        if result.is_ok():
            print(f"Page title: {result.default_value(None)}")
        else:
            print(f"Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuring the Browser

Silk supports different browser drivers. You can configure them like this:

```python
from silk.models.browser import BrowserOptions
from silk.browsers.manager import BrowserManager

# Configure browser options
options = BrowserOptions(
    headless=False,  # Set to False to see the browser UI
    browser_name="chromium",  # Choose "chromium", "firefox", or "webkit"
    slow_mo=50,  # Slow down operations by 50ms (useful for debugging)
    viewport={"width": 1280, "height": 800}
)

# Create a manager with specific driver and options
manager = BrowserManager(driver_type="playwright", default_options=options)
```

### Creating Custom Actions

You can easily create your own actions for reusable scraping logic:

```python
from silk.actions.base import Action
from silk.actions.decorators import action
from expression.core import Ok, Error
from silk.models.browser import ActionContext

@action()
async def extract_price(context, selector):
    """Extract and parse a price from the page"""
    page_result = await context.get_page()
    if page_result.is_error():
        return page_result
        
    page = page_result.default_value(None)
    if page is None:
        return Error("No page found")   
    
    element_result = await page.query_selector(selector)
    
    if element_result.is_error():
        return Error(f"Element not found: {selector}")
        
    element = element_result.default_value(None)
    if element is None:
        return Error("No element found")
    
    text_result = await element.get_text()
    
    if text_result.is_error():
        return text_result
        
    text = text_result.default_value(None)
    if text is None:
        return Error("No text found")
    
    try:
        # Remove currency symbol and convert to float
        price = float(text.replace('$', '').strip())
        return Ok(price)
    except ValueError:
        return Error(f"Failed to parse price from: {text}")
```

## Core Concepts

### Actions

The fundamental building block in Silk is the `Action`. An Action represents a pure operation that can be composed with other actions using functional programming patterns. Each Action takes an `ActionContext` and returns a `Result` containing either the operation's result or an error.

```python
class FindElement(Action[ElementHandle]):
    """Action to find an element on the page"""
    
    def __init__(self, selector: str):
        self.selector = selector
        
    async def execute(self, context: ActionContext) -> Result[ElementHandle, Exception]:
        try:
            page_result = await context.get_page()
            if page_result.is_error():
                return page_result
                
            page = page_result.default_value(None)
            if page is None:
                return Error("No page found")
            
            return await page.query_selector(self.selector)
        except Exception as e:
            return Error(e)
```

### ActionContext

The `ActionContext` carries references to the browser, page, and other execution context information. Actions use this context to interact with the browser.

### Result Type

Silk uses the `Result[T, E]` type from the Expression library for error handling. Rather than relying on exceptions, actions return `Ok(value)` for success or `Error(exception)` for failures.

### Composition Operators

Silk provides powerful operators for composing actions:

- **`>>`** (then): Chain actions sequentially
- **`&`** (and): Run actions in parallel
- **`|`** (or): Try one action, fall back to another if it fails

These operators make it easy to build complex scraping workflows with clear, readable code.

## Real-World Examples: The Power of Composition

### E-commerce Product Monitoring

```python
# Define reusable extraction component
extract_product_data = (
    GetText(".product-title") &
    GetText(".product-price") &
    GetAttribute(".product-image", "src") &
    GetText(".stock-status")
)

# Define a complete scraping pipeline for a single product
scrape_product = (
    Navigate(product_url)
    >> Wait(1000)  # Wait for dynamic content
    >> extract_product_data
    >> ParseProductData()  # Custom action to transform raw data
)

# Scale to multiple products effortlessly
scrape_multiple_products = parallel(*(
    scrape_product(url) for url in product_urls
))

# Add resilience with minimal changes
resilient_product_scraper = retry(
    scrape_product,
    max_attempts=3,
    delay_ms=1000
)
```

### Handling Complex User Flows

```python
# Define composable steps for a checkout process
add_to_cart = (
    Click(".add-to-cart-button")
    >> Wait(500)
    >> ElementExists(".cart-confirmation")
)

proceed_to_checkout = (
    Navigate("/cart")
    >> Click(".checkout-button")
    >> Wait(1000)
)

fill_shipping_form = (
    Fill("#first-name", customer.first_name)
    >> Fill("#last-name", customer.last_name)
    >> Fill("#address", customer.address)
    >> Fill("#city", customer.city)
    >> Select("#country", customer.country)
    >> Fill("#postal-code", customer.postal_code)
    >> Click(".continue-button")
)

# Combine into a complete checkout pipeline
checkout_pipeline = (
    Navigate(product_url)
    >> add_to_cart
    >> proceed_to_checkout
    >> fill_shipping_form
    >> verify_checkout_details
    >> complete_payment
)
```

## Additional examples and sections would continue below...