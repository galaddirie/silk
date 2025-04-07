# Silk

[![PyPI version](https://img.shields.io/badge/pypi-v0.1.0-blue.svg)](https://pypi.org/project/silk-scraper/)
[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/silk-scraper/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type check: mypy](https://img.shields.io/badge/type%20check-mypy-blue)](https://github.com/python/mypy)

**Silk** is a functional web scraping framework for Python with a focus on composability, resilience, and developer experience. Built on the [Expression](https://github.com/dbrattli/Expression) library, Silk lets you build complex scraping workflows with elegant, readable code and true functional programming patterns.

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
pip install silk

# With Playwright support
pip install silk[playwright]

# With Selenium support
pip install silk[selenium]

# With Puppeteer support
pip install silk[puppeteer]

# With all drivers
pip install silk[all]
```

## Quick Start

// todo


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
navigate(url) >> extract_text(title_selector)
```

### Parallel Operations (`&`)

```python
# Extract name, price, and description in parallel
extract_text(name_selector) & extract_text(price_selector) & extract_text(description_selector)
```

### Fallback Operations (`|`)

```python
# Try to extract with one selector, fall back to another if it fails
extract_text(primary_selector) | extract_text(fallback_selector)
```

## Architecture

Silk consists of several interconnected components:

1. **Browser Driver**: Abstract interface for browser automation
2. **Selectors**: CSS, XPath, and other selection strategies with fallback mechanisms
3. **Actions**: Pure functions wrapped as composable objects with railway-oriented result handling
4. **Combinators**: Functions like `sequence_actions`, `parallel_actions`, and `fallback_actions`
5. **Engine**: Orchestration of browser instances and pipeline execution




## License

Silk is released under the MIT License. See the [LICENSE](LICENSE) file for details.
