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

Here's a simple example to scrape a product from an e-commerce site:

```python
from silk import navigate, extract_text, extract_attr, parallel, Browser
from silk.selectors import css, select_group
from expression import pipe

# Define selectors with fallbacks
product_name = select_group(
    "product_name",
    css(".product-title h1"),
    css(".product-name")
)

# Create a pipeline using composable operators
product_pipeline = (
    navigate("https://example.com/product/123")
    >> extract_text(product_name)
    >> extract_attr(css(".product-image img"), "src")
    >> (lambda results: {
        "name": results[0],
        "image_url": results[1]
    })
)

# Execute the pipeline
async def main():
    async with Browser.playwright() as browser:
        result = await product_pipeline(browser)
        # Railway-oriented programming - handle success and error paths
        if result.is_ok():
            print(f"Successfully scraped: {result.unwrap()}")
        else:
            print(f"Error: {result.error()}")

# Run the scraper
import asyncio
asyncio.run(main())
```

## Functional Programming with Silk

Silk is built on functional programming principles, powered by the Expression library:

### Railway-Oriented Programming

Actions in Silk return `Result[T, Exception]` types that elegantly handle the "happy path" and "error path":

```python
# Actions return Result types that can be either Ok or Error
result = await extract_text(selector)(driver)

# Handle both paths with pattern matching
if result.is_ok():
    text = result.unwrap()
    print(f"Extracted text: {text}")
else:
    print(f"Extraction failed: {result.error()}")
```

### Immutable Data Structures

Silk uses Expression's immutable collections like `Block` instead of Python's mutable lists:

```python
from expression.collections import Block

# No side effects or unexpected mutations
extracted_items = Block.of_seq(["item1", "item2"])
new_items = extracted_items.cons("item0")  # Creates a new Block

# Use pipe for functional transformations
from expression import pipe
transformed = pipe(
    extracted_items,
    Block.map(lambda x: x.upper()),
    Block.filter(lambda x: len(x) > 4)
)
```

### Action Decorator for Custom Functions

Easily convert any function into a composable Action using the `@action` decorator:

```python
from silk import action, Ok, Error

# Create a custom action with the decorator
@action(name="scroll_to_element")
async def scroll_to_element(driver, selector, smooth=True):
    """Scrolls the page to bring the element into view"""
    try:
        element = await driver.query_selector(selector)
        await element.scroll_into_view({"behavior": "smooth" if smooth else "auto"})
        return "Element scrolled into view"
    except Exception as e:
        # The decorator will handle this exception and convert it to Error
        raise e

# Use it in a pipeline - the function is now a composable Action!
pipeline = (
    navigate(url)
    >> scroll_to_element("#my-element")
    >> extract_text("#my-element")
)

# Result handling happens automatically
result = await pipeline(browser)
if result.is_ok():
    print(f"Extracted text after scrolling: {result.unwrap()}")
```

The action decorator:
- Automatically wraps functions with railway-oriented error handling
- Works with both sync and async functions
- Preserves function signatures and docstrings
- Makes your functions fully composable with other Silk actions

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

## Advanced Usage

### Parallel Scraping with Immutability

```python
from silk import parallel
from expression.collections import Block

# Create pipelines for different products
product_pipelines = Block.of_seq([create_product_pipeline(url) for url in urls])

# Execute all pipelines in parallel
results = await parallel(*product_pipelines)(browser)
```

### Robust Error Handling with Railway Pattern

```python
from silk import retry, fallback_actions
from expression.core import Ok, Error

# Retry a pipeline multiple times
resilient_pipeline = retry(my_pipeline, max_attempts=3, delay_ms=1000)

# Try different pipelines in sequence
fallback_pipeline = fallback_actions(
    primary_pipeline,
    backup_pipeline,
    last_resort_pipeline
)

# Custom error handler
result = await resilient_pipeline(browser)
if result.is_error():
    # Handle specific error types
    if isinstance(result.error(), TimeoutError):
        print("Operation timed out")
    else:
        print(f"Operation failed: {result.error()}")
```

### Custom Actions

```python
from silk.actions import Action
from expression.core import Ok, Error

class MyCustomAction(Action[str]):
    def __init__(self, param: str):
        super().__init__(name=f"custom({param})")
        self.param = param
    
    async def execute(self, driver):
        try:
            # Custom implementation
            return Ok(f"Result: {self.param}")
        except Exception as e:
            return Error(e)

# Use your custom action in a pipeline
pipeline = navigate(url) >> MyCustomAction("test")
```

## API Documentation

For detailed API documentation, visit our [documentation site](https://silk-scraper.readthedocs.io/).

### Main Components

- `Browser`: Abstract browser interface with implementations for Playwright, Selenium, etc.
- `Selector`: Represents a way to find elements (CSS, XPath, ID, etc.)
- `SelectorGroup`: Combines multiple selectors with fallbacks
- `Action`: Base class for all actions (navigation, extraction, etc.)
- `Expression Types`: Result, Option, Block and other functional types from the Expression library

## Contributing

Contributions are welcome! Check out the [contribution guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/silk.git
cd silk

# Set up a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run type checking
mypy src/silk
```

### Type Checking

This project uses mypy for static type checking. We enforce strict type checking to ensure code quality and catch potential bugs early.

To run the type checker:

```bash
# Run mypy on the project
./scripts/run_mypy.sh

# Or directly
mypy src/silk
```

The project configuration uses strict typing rules including:
- No untyped definitions or decorators
- Warning on returning Any
- No implicit optional types
- Strict optional checking

## License

Silk is released under the MIT License. See the [LICENSE](LICENSE) file for details.




navigate 