# Silk

[![PyPI version](https://img.shields.io/badge/pypi-v0.1.0-blue.svg)](https://pypi.org/project/silk-scraper/)
[![Python versions](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/silk-scraper/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type check: mypy](https://img.shields.io/badge/type%20check-mypy-blue)](https://github.com/python/mypy)

**Silk** is a functional web scraping framework for Python that reimagines how web automation should work. Built around composable "Actions" and the [Expression](https://github.com/dbrattli/Expression) library, Silk enables you to write elegant, maintainable, and resilient web scrapers with true functional programming patterns.

Unlike traditional scraping libraries, Silk embraces Railway-Oriented Programming for robust error handling, uses immutable data structures for predictability, and provides an expressive, composable API that makes even complex scraping workflows readable and maintainable.

## Why Silk?

Traditional web scraping approaches in Python often lead to complex, brittle code that's difficult to maintain. Silk solves these common challenges:

- **No More Callback Hell**: Replace nested try/except blocks with elegant Railway-Oriented Programming
- **Resilient Scraping**: Built-in retry mechanisms, fallback selectors, and error recovery
- **Composable Actions**: Chain operations with intuitive operators (`>>`, `&`, `|`) for cleaner code
- **Type-Safe**: Full typing support with Mypy and Pydantic for fewer runtime errors
- **Browser Agnostic**: Same API for Playwright, Selenium, or any other browser automation tool
- **Parallelization Made Easy**: Run operations concurrently with the `&` operator

Whether you're building a small data collection script or a large-scale scraping system, Silk's functional approach scales with your needs while keeping your codebase clean and maintainable.

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
        result = await manager.execute_action(pipeline)
        
        if result.is_ok():
            print(f"Page title: {result.unwrap()}")
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
        
    page = page_result.unwrap()
    element_result = await page.query_selector(selector)
    
    if element_result.is_error():
        return Error(f"Element not found: {selector}")
        
    element = element_result.unwrap()
    text_result = await element.get_text()
    
    if text_result.is_error():
        return text_result
        
    text = text_result.unwrap()
    
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
                
            page = page_result.unwrap()
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

## Detailed Examples

### Handling Complex Selectors

Silk provides robust ways to handle changing website structures with selector groups. Selector groups are a collection of selectors that are tried in order until one succeeds.

```python
from silk.selectors.selector import SelectorGroup, css, xpath

# Create a selector group with fallback options
product_price = SelectorGroup.create(
    "product_price",
    css(".current-price"),             # Try this first
    css(".product-price .amount"),     # Fall back to this
    xpath("//div[contains(@class, 'price')]//span")  # Last resort
)

# Use it in an extraction action
extract_price = GetText(product_price)
```

### Resilient Scraping with Retry and Fallbacks

```python
from silk.actions.flow import retry, fallback
from silk.actions.extraction import GetText
from silk.actions.navigation import Navigate

# Retry navigation up to 3 times with 2s delay
resilient_navigation = retry(
    Navigate("https://example.com"),
    max_attempts=3,
    delay_ms=2000
)

# Try multiple selectors for extracting data
extract_title = fallback(
    GetText(".main-title"),
    GetText("h1.title"),
    GetText("#product-name")
)

# Combine into a pipeline
pipeline = resilient_navigation >> extract_title
```

### Parallel Extraction

Extract multiple pieces of information at once:

```python
from silk.actions.composition import parallel
from silk.actions.extraction import GetText, GetAttribute

# Extract product details in parallel
product_details = parallel(
    GetText(".product-name"),
    GetText(".product-price"),
    GetAttribute(".product-image", "src"),
    GetText(".product-description")
)

# Use in a pipeline
pipeline = Navigate(product_url) >> product_details

# Results come back as a Block collection
result = await manager.execute_action(pipeline)
if result.is_ok():
    [name, price, image_url, description] = result.unwrap()
    print(f"Product: {name}, Price: {price}")
```

### Form Filling and Submission

```python
from silk.actions.input import Fill, Click
from silk.actions.flow import compose

login_action = compose(
    Navigate("https://example.com/login"),
    Fill("#username", "user@example.com"),
    Fill("#password", "password123"),
    Click("button[type='submit']")
)
```

### Handling Dynamic Content

```python
from silk.actions.flow import wait, loop_until
from silk.actions.conditions import ElementExists

# Wait for dynamic content to load
wait_for_results = wait(1000) >> ElementExists(".search-results-item")

# Loop until a condition is met
load_all_results = loop_until(
    condition=ElementExists(".no-more-results"),
    body=Click(".load-more-button"),
    max_iterations=10,
    delay_ms=1000
)

# Use in a pipeline
search_pipeline = (
    Navigate("https://example.com/search?q=example")
    >> wait_for_results
    >> load_all_results
    >> GetText(".search-results-count")
)
```

### Action Decorator for Custom Functions

Easily convert any function into a composable Action using the `@action` decorator:

```python
from silk import action, Ok, Error

@action
async def scroll_to_element(driver, selector, smooth=True):
    """Scrolls the page to bring the element into view"""
    try:
        element = await driver.query_selector(selector)
        await element.scroll_into_view({"behavior": "smooth" if smooth else "auto"})
        return "Element scrolled into view"
    except Exception as e:
        raise e

# Use it in a pipeline - the function is now a composable Action!
pipeline = (
    Navigate(url)
    >> scroll_to_element("#my-element")
    >> extract_text("#my-element")
)

result = await pipeline(browser)
if result.is_ok():
    print(f"Extracted text after scrolling: {result.unwrap()}")
```

## Composable Operations

Silk provides intuitive operators for composable scraping:

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

## API Reference

### Core Modules

- **`silk.actions`**: Core action classes for browser automation
  - **`silk.actions.base`**: Base Action class and core utilities
  - **`silk.actions.navigation`**: Actions for navigating between pages
  - **`silk.actions.extraction`**: Actions for extracting data from pages
  - **`silk.actions.input`**: Actions for interacting with forms and elements
  - **`silk.actions.flow`**: Control flow actions like branch, retry, and loop
  - **`silk.actions.composition`**: Utilities for composing actions (sequence, parallel, pipe)
  - **`silk.actions.decorators`**: Decorators like @action for creating custom actions

- **`silk.browsers`**: Browser management and abstraction layer
  - **`silk.browsers.manager`**: BrowserManager for session handling
  - **`silk.browsers.driver`**: Abstract BrowserDriver interface
  - **`silk.browsers.element`**: ElementHandle for working with DOM elements
  
- **`silk.selectors`**: Selector utilities
  - **`silk.selectors.selector`**: Selector and SelectorGroup classes

- **`silk.models`**: Data models using Pydantic
  - **`silk.models.browser`**: BrowserOptions, ActionContext, etc.

### Common Action Classes

- **Navigation**
  - `Navigate(url)`: Navigate to a URL
  - `Reload()`: Reload the current page
  - `GoBack()`: Navigate back in history
  - `GoForward()`: Navigate forward in history

- **Extraction**
  - `Query(selector)`: Find an element
  - `QueryAll(selector)`: Find all matching elements
  - `GetText(selector)`: Extract text from an element
  - `GetAttribute(selector, attribute)`: Get an attribute value
  - `GetHtml(selector, outer=True)`: Get element HTML
  - `ExtractTable(table_selector)`: Extract data from an HTML table

- **Input**
  - `Click(target)`: Click an element
  - `DoubleClick(target)`: Double-click an element
  - `Fill(target, text)`: Fill a form field
  - `Type(target, text)`: Type text (alias for Fill)
  - `Select(target, value/text)`: Select an option from a dropdown
  - `MouseMove(target)`: Move the mouse to an element
  - `KeyPress(key, modifiers)`: Press a key or key combination

- **Flow Control**
  - `branch(condition, if_true, if_false)`: Conditional branching
  - `loop_until(condition, body, max_iterations)`: Loop until condition is met
  - `retry(action, max_attempts, delay_ms)`: Retry an action on failure
  - `retry_with_backoff(action)`: Retry with exponential backoff
  - `with_timeout(action, timeout_ms)`: Apply a timeout to an action

- **Composition**
  - `sequence(*actions)`: Run actions in sequence, collect all results
  - `parallel(*actions)`: Run actions in parallel, collect all results
  - `pipe(*actions)`: Create a pipeline where each action uses the previous result
  - `fallback(*actions)`: Try actions in sequence until one succeeds
  - `compose(*actions)`: Compose actions sequentially, return only the last result

For a complete API reference, please see the [API documentation](https://silk-docs.example.com).

## Best Practices

### Error Handling

Silk uses Railway-Oriented Programming for error handling. Instead of using try/except, leverage the Result type:

```python
result = await manager.execute_action(pipeline)
if result.is_ok():
    data = result.unwrap()
    # Process the data
else:
    # Handle the error
    error = result.error
    logger.error(f"Scraping failed: {error}")
```

### Browser Resources

Always use context managers to ensure browser resources are properly cleaned up:

```python
async with BrowserManager() as manager:
    # Your scraping code here
    pass  # Resources automatically cleaned up
```

### Selector Resilience

Use selector groups for resilient scraping that can handle UI changes:

```python
# Instead of a single brittle selector:
extract_price = GetText(".price-box .price")

# Use a group with fallbacks:
price_selector = SelectorGroup.create(
    "price",
    css(".price-box .price"),
    css(".product-price"),
    xpath("//span[contains(@class, 'price')]")
)
extract_price = GetText(price_selector)
```

### Action Composition

Build reusable pipelines through composition instead of large monolithic functions:

```python
# Define reusable components
navigate_to_product = Navigate("https://example.com/product")
extract_product_info = parallel(
    GetText(".product-name"),
    GetText(".product-price"),
    GetText(".product-description")
)
extract_related_products = QueryAll(".related-product") >> extract_text_from_elements

# Compose them in different ways
full_scraper = navigate_to_product >> extract_product_info >> extract_related_products
minimal_scraper = navigate_to_product >> extract_product_info
```

### Logging

Enable logging to better debug your scraping pipelines:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("silk").setLevel(logging.DEBUG)
```

## Contributing

Contributions to Silk are welcome! Please feel free to submit a Pull Request.

### Development Setup

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/silk.git
   cd silk
   ```

2. Create a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies
   ```bash
   pip install -e ".[dev,test,all]"
   ```

4. Run tests
   ```bash
   pytest
   ```

### Guidelines

- Follow PEP 8 and use Black for code formatting
- Write tests for new features
- Keep the functional programming paradigm in mind
- Update documentation with new features

## Acknowledgements

Silk builds upon several excellent libraries:
- [Expression](https://github.com/dbrattli/Expression) for functional programming patterns in Python
- [Playwright](https://playwright.dev/) and [Selenium](https://www.selenium.dev/) for browser automation
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation and settings management

## Roadmap

- [x] Initial release with Playwright support
- [x] Selenium integration
- [ ] Puppeteer integration
- [ ] Data extraction DSL for declarative scraping
- [ ] Enhanced caching mechanisms
- [ ] Distributed scraping support
- [ ] Rate limiting and polite scraping utilities
- [ ] Integration with popular data processing libraries (Pandas, etc.)
- [ ] CLI tool for quick scraping tasks

## FAQ

### How does Silk compare to other scraping libraries?

Silk differs from traditional scraping libraries like Scrapy, Beautiful Soup, or plain Selenium/Playwright in its functional approach. While these tools focus on imperative code with callbacks and exceptions, Silk embraces functional composition, immutable data structures, and Railway-Oriented Programming for cleaner, more maintainable code.

### Can I use Silk with my existing Playwright/Selenium code?

Yes, Silk is designed to work alongside existing browser automation code. You can gradually adopt Silk's patterns while keeping your existing code.

### Is Silk suitable for large-scale scraping?

Absolutely. Silk's composable nature makes it excellent for large-scale scraping projects. Its built-in error handling, retries, and parallel execution capabilities are particularly valuable for robust production systems.

### How can I handle authentication in Silk?

You can handle authentication like any other browser interaction:

```python
login_action = compose(
    Navigate("https://example.com/login"),
    Fill("#username", "user@example.com"),
    Fill("#password", "password123"),
    Click("button[type='submit']"),
    wait(1000)  # Wait for login to complete
)

# Then use the authenticated context for further actions
pipeline = login_action >> Navigate("https://example.com/protected-content") >> GetText("#protected-data")
```

You can also save and reuse authentication state with browser context options.

## License

Silk is released under the MIT License. See the [LICENSE](LICENSE) file for details.