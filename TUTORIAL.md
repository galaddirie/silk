# Silk Framework Tutorial

A concise guide to using the Silk web scraping framework.

## Installation

```bash
pip install silk-scraper
pip install silk-scraper[playwright]  # For Playwright support
```

## Quick Start

```python
import asyncio
from silk.actions.navigation import Navigate
from silk.actions.extraction import GetText
from silk.browsers.manager import BrowserManager

async def main():
    async with BrowserManager() as manager:
        pipeline = Navigate("https://example.com") >> GetText("h1")
        result = await pipeline(manager)
        print(result.default_value("Not found"))

asyncio.run(main())
```

## Core Concepts

### Actions
- Pure operations that form scraping building blocks
- Take `ActionContext` as input
- Return `Result` containing value or error
- Composable using operators

### Composition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `>>` | Sequential execution | `Navigate(url) >> GetText(selector)` |
| `&` | Parallel execution (separate contexts) | `GetText(title) & GetText(price)` |
| `|` | Fallback execution | `GetText(primary) | GetText(fallback)` |

## Available Actions

### Navigation
- `Navigate(url)`: Load a webpage
- `GoBack()`: Go back in history
- `GoForward()`: Go forward in history
- `Refresh()`: Refresh current page
- `WaitForSelector(selector)`: Wait for an element to appear
- `WaitForNavigation()`: Wait for page navigation to complete
- `WaitForFunction(js_function)`: Wait for JavaScript function to return true
- `GetCurrentUrl()`: Get the current page URL
- `GetPageSource()`: Get the full HTML source of the page
- `ExecuteScript(script, *args)`: Execute JavaScript on the page
- `Screenshot(path)`: Save a screenshot

### Extraction
- `Query(selector)`: Get a single element handle
- `QueryAll(selector)`: Get a list of element handles
- `ElementExists(selector)`: Check if an element exists (often used with `branch`)
- `GetText(selector)`: Get element text content
- `GetInnerText(selector)`: Get element's visible text content
- `GetAttribute(selector, attr)`: Get element attribute value
- `GetHtml(selector)`: Get element's inner or outer HTML
- `ExtractTable(selector)`: Extract data from an HTML table
- `Evaluate(script, *args)`: Evaluate JavaScript in the page context

### Input
- `Click(selector)`: Click an element
- `DoubleClick(selector)`: Double-click an element
- `Fill(selector, text)`: Fill an input field (clears existing value)
- `Type(selector, text)`: Type text into an element (simulates key presses)
- `Select(selector, value?, text?)`: Select an option from a dropdown
- `KeyPress(key, modifiers?)`: Press a key (e.g., 'Enter')
- `MouseMove(target, offset_x?, offset_y?)`: Move mouse cursor
- `MouseDown(button?)`: Press a mouse button
- `MouseUp(button?)`: Release a mouse button
- `Drag(source, target)`: Drag an element or position to another

### Flow Control
- `wait(ms)`: Pause execution for a specified time
- `retry(action, max_attempts, delay_ms)`: Retry a failed action
- `retry_with_backoff(action, ...)`: Retry with exponential backoff
- `branch(condition, if_true, if_false)`: Conditional execution
- `loop_until(condition, body, max_iterations)`: Loop until condition met
- `with_timeout(action, timeout_ms)`: Execute an action with a timeout
- `log(message, level?)`: Log a message during execution
- `tap(main_action, side_effect)`: Execute a side-effect action without affecting the main result

## Selectors

Selectors identify elements on the page. Silk supports various types.

### Creating Selectors
```python
from silk.selectors.selector import css, xpath, text, SelectorGroup

# Basic selectors
title_selector = css("h1.product-title")
price_xpath = xpath("//span[@class='price']")
button_text = text("Add to Cart")

# Selector Group for fallbacks
robust_title = SelectorGroup(
    "main_title",
    css(".main-heading"),
    xpath("//header/h1"),
    css("#productTitle")
)

# Use in actions
GetText(title_selector)
Click(button_text)
GetAttribute(robust_title, "id")
```

## Composition Functions

Use these functions for more complex orchestrations.

### Basic Composition
```python
from silk.actions.composition import sequence, parallel, pipe, fallback

# Sequential execution, returns Block[result1, result2]
sequence(GetText(".title"), GetText(".price"))

# Parallel execution (new context for each), returns Block[result1, result2]
parallel(Navigate("site1.com") >> GetText("h1"), Navigate("site2.com") >> GetText("h1"))

# Pipeline: result of one action passed to the next
# Example: Get price text "$10.99", pass to parse_price action
pipe(GetText(".price"), parse_price) # parse_price is a custom @action

# Fallback execution (functional equivalent of '|')
fallback(GetText(".sale-price"), GetText(".regular-price"))

# Compose: Sequential execution, returns only the *last* result
compose(Navigate(url), Click(".link"), GetText(".final-data"))
```

## Browser & Context Management

The `BrowserManager` handles browser instances and contexts (like isolated sessions).

### Basic Usage
```python
from silk.models.browser import BrowserOptions
from silk.browsers.manager import BrowserManager

options = BrowserOptions(headless=False, browser_type="chromium")
manager = BrowserManager(default_options=options)

async with manager: # Ensures browser cleanup
    # Create context manually if needed
    context_result = await manager.create_context(nickname="user_session")
    if context_result.is_ok():
        context = context_result.default_value()
        # ... use context.id in actions or switch context

    # Actions typically handle context creation automatically when called with manager
    result = await (Navigate(url) >> GetText("h1"))(manager)
```

### Context Actions (Optional)
```python
from silk.actions.context import CreateContext, SwitchContext, CloseContext, CreatePage, SwitchPage

# Example: Create and switch between contexts/pages
pipeline = (
    CreateContext(nickname="context1")
    >> Navigate("site1.com")
    >> CreatePage(nickname="page2") # Creates page in context1
    >> Navigate("site1.com/details")
    >> CreateContext(nickname="context2") # Creates a new isolated context
    >> SwitchContext("context1") # Switch back
    >> SwitchPage("page2") # Switch back to the second page in context1
    # ...
)
```

## Creating Custom Actions

Use the `@action()` decorator for custom logic.

```python
from silk.actions.decorators import action
from expression.core import Ok, Error

@action()
async def parse_price(context: ActionContext, price_text: str):
    # Your custom parsing logic
    try:
        price = float(price_text.replace('$', '').strip())
        return Ok(price) # Must return Ok() or Error()
    except ValueError as e:
        return Error(Exception(f"Failed to parse price: {price_text}, Error: {e}"))

# Use in a pipeline
get_price = Navigate(url) >> GetText(".price") >> parse_price()
```

## Best Practices

1. Use `SelectorGroup` for resilient element selection.
2. Use `retry` or `retry_with_backoff` for network-dependent or flaky operations.
3. Use `parallel` for independent scraping tasks (e.g., scraping multiple sites).
4. Handle errors gracefully using `Result` methods (`is_ok()`, `is_error()`, `default_value()`).
5. Keep actions focused; compose small actions for complex logic.

## Common Patterns

### Product Scraping
```python
from silk.actions.extraction import GetAttribute # Ensure import

product_scraper = (
    Navigate(url)
    >> wait(1000) # Use flow.wait if needed
    >> (GetText(".title") & GetText(".price") & GetAttribute(".image", "src"))
    # >> ParseProductData() # Example custom action
).with_retry(max_attempts=3) # Assumes Action has with_retry method or use flow.retry
```

### Form Submission
```python
from silk.actions.input import Fill, Click # Ensure imports
from silk.actions.flow import wait # Ensure import

login_flow = (
    Navigate(login_url)
    >> Fill("#username", "user")
    >> Fill("#password", "pass")
    >> Click("button[type='submit']")
    >> wait(1000)
)
```

### Pagination
```python
from silk.actions.extraction import ElementExists # Ensure import
from silk.actions.input import Click # Ensure import
from silk.actions.flow import loop_until, wait # Ensure imports

pagination_flow = loop_until(
    condition=ElementExists(".next-page"), # Condition to check
    body=Click(".next-page") >> wait(1000), # Action to repeat
    max_iterations=10
)
``` 