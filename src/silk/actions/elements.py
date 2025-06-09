"""
Extraction actions for retrieving data from web pages.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Union, cast, Callable

from expression import Error, Ok, Result
from fp_ops import operation

from silk.actions.utils import resolve_target, validate_driver
from silk.browsers.models import ActionContext, ElementHandle, Page, WaitOptions, Driver
from silk.selectors.selector import Selector, SelectorGroup

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def _resolve_parent(
    context: ActionContext,
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]]
) -> Result[Optional[ElementHandle], Exception]:
    """Helper to resolve parent element if provided."""
    if parent is None:
        return Ok(None)
    
    parent_result = await resolve_target(context, parent)
    if parent_result.is_error():
        return Error(parent_result.error)
    
    parent_element = parent_result.default_value(None)
    if parent_element is None:
        return Error(Exception("Parent element not found"))
    
    return Ok(parent_element)


async def _query_single_element(
    selector: Union[str, Selector, SelectorGroup],
    query_func: Callable,
    parent_element: Optional[ElementHandle] = None,
    page: Optional[Page] = None
) -> Result[Optional[ElementHandle], Exception]:
    """Helper to query a single element with various selector types."""
    if not parent_element and not page:
        return Error(Exception("No target (parent or page) provided"))

    
    if isinstance(selector, str):
        result = await query_func(selector)
        if result.is_error():
            return Error(result.error)
        element = result.default_value(None)
        if element is None:
            return Error(Exception(f"No element found for selector: {selector}"))
        return Ok(element)
    
    if isinstance(selector, Selector):
        result = await query_func(selector.value)
        if result.is_error():
            return Error(result.error)
        element = result.default_value(None)
        if element is None:
            return Error(Exception(f"No element found for selector: {selector.value}"))
        return Ok(element)
    
    if isinstance(selector, SelectorGroup):
        for sel in selector.selectors:
            sub = await query_func(sel.value)
            if sub.is_error():
                continue
            element = sub.default_value(None)
            if element is not None:
                return Ok(element)
        return Error(Exception(f"No element found for any selector in group: {selector}"))
    
    return Error(Exception(f"Unsupported selector type: {type(selector)}"))


async def _query_all_elements(
    selector: Union[str, Selector, SelectorGroup],
    query_func: Callable,
    parent_element: Optional[ElementHandle] = None,
    page: Optional[Page] = None
) -> Result[List[ElementHandle], Exception]:
    """Helper to query multiple elements with various selector types."""
    if not parent_element and not page:
        return Error(Exception("No target (parent or page) provided"))
    
    if isinstance(selector, str):
        result = await query_func(selector)
        if result.is_error():
            return Error(result.error)
        elements = result.default_value(None)
        return Ok(elements if elements is not None else [])
    
    if isinstance(selector, Selector):
        result = await query_func(selector.value)
        if result.is_error():
            return Error(result.error)
        elements = result.default_value(None)
        return Ok(elements if elements is not None else [])
    
    if isinstance(selector, SelectorGroup):
        all_elements = []
        for sel in selector.selectors:
            sub_result = await query_func(sel.value)
            if sub_result.is_error():
                continue
            elements = sub_result.default_value(None)
            if elements:
                all_elements.extend(elements)
        return Ok(all_elements)
    
    return Error(Exception(f"Unsupported selector type: {type(selector)}"))


async def _find_element_with_parent(
    context: ActionContext,
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None
) -> Result[Optional[ElementHandle], Exception]:
    """Helper to find an element, optionally within a parent."""
    # If selector is already an ElementHandle, return it
    if isinstance(selector, ElementHandle):
        return Ok(selector)
    
    # Resolve parent if provided
    parent_result = await _resolve_parent(context, parent)
    if parent_result.is_error():
        return Error(parent_result.error)
    
    parent_element = parent_result.default_value(None)
    
    if parent_element:
        # Query within parent
        return await _query_single_element(
            selector,
            parent_element.query_selector,
            parent_element=parent_element
        )
    else:
        # Query page-wide
        if context.page is None:
            return Error(Exception("No page found"))
        
        return await _query_single_element(
            selector,
            context.page.query_selector,
            page=context.page
        )


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def Query(
    selector: Union[str, Selector, SelectorGroup],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Optional[ElementHandle], Exception]:
    """
    Action to query a single element

    Args:
        selector: Selector to find element
        parent: Optional parent element to search within

    Returns:
        Found element or None if not found
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        return await _find_element_with_parent(context, selector, parent)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def QueryAll(
    selector: Union[str, Selector, SelectorGroup],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[List[ElementHandle], Exception]:
    """
    Action to query multiple elements

    Args:
        selector: Selector to find elements
        parent: Optional parent element to search within

    Returns:
        List of found elements (empty if none found)
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        # Resolve parent if provided
        parent_result = await _resolve_parent(context, parent)
        if parent_result.is_error():
            return Error(parent_result.error)
        
        parent_element = parent_result.default_value(None)
        
        if parent_element:
            # Query within parent
            return await _query_all_elements(
                selector,
                parent_element.query_selector_all,
                parent_element=parent_element
            )
        else:
            # Query page-wide
            if context.page is None:
                return Error(Exception("No page found"))
            
            return await _query_all_elements(
                selector,
                context.page.query_selector_all,
                page=context.page
            )
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetText(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Optional[str], Exception]:
    """
    Action to get text from an element

    Args:
        selector: Selector to find element
        parent: Optional parent element to search within

    Returns:
        Text content of the element or None if element not found
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        # Find the element
        element_result = await _find_element_with_parent(context, selector, parent)
        if element_result.is_error():
            return Ok(None)
        
        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        # Get text from element
        text_result = await element.get_text()
        if text_result.is_error():
            return Error(text_result.error)

        return Ok(text_result.default_value(""))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetAttribute(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    attribute: str,
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Optional[str], Exception]:
    """
    Action to get an attribute from an element

    Args:
        selector: Selector to find element
        attribute: Attribute name to get
        parent: Optional parent element to search within

    Returns:
        Attribute value or None if element not found or attribute not present
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        # Find the element
        element_result = await _find_element_with_parent(context, selector, parent)
        if element_result.is_error():
            return Ok(None)
        
        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        # Get attribute from element
        attr_result = await element.get_attribute(attribute)
        if attr_result.is_error():
            return Error(attr_result.error)

        return Ok(attr_result.default_value(""))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetHtml(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    outer: bool = True,
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Optional[str], Exception]:
    """
    Action to get HTML content from an element

    Args:
        selector: Selector to find element
        outer: Whether to include the element's outer HTML
        parent: Optional parent element to search within

    Returns:
        HTML content of the element or None if element not found
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        # Find the element
        element_result = await _find_element_with_parent(context, selector, parent)
        if element_result.is_error():
            return Ok(None)
        
        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        # Get HTML from element
        html_result = await element.get_html(outer=outer)
        if html_result.is_error():
            return Error(html_result.error)

        return Ok(html_result.default_value(""))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def GetInnerText(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Optional[str], Exception]:
    """
    Action to get the innerText from an element (visible text only)

    Args:
        selector: Selector to find element
        parent: Optional parent element to search within

    Returns:
        Inner text of the element or None if element not found
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        if context.page_id is None:
            return Error(Exception("No page ID found"))

        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        # Find the element
        element_result = await _find_element_with_parent(context, selector, parent)
        if element_result.is_error():
            return Ok(None)
        
        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        # Get innerText using JavaScript
        selector_str = element.get_selector()
        if not selector_str:
            return Error(Exception("Could not get element selector"))

        js_result = await driver.execute_script(
            context.page_id, f"document.querySelector('{selector_str}').innerText"
        )

        if js_result.is_error():
            return Error(js_result.error)

        return Ok(js_result.default_value(""))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def ExtractTable(
    table_selector: Union[str, Selector, SelectorGroup],
    include_headers: bool = True,
    header_selector: Optional[str] = None,
    row_selector: Optional[str] = None,
    cell_selector: Optional[str] = None,
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[List[Dict[str, str]], Exception]:
    """
    Action to extract data from an HTML table

    Args:
        table_selector: Selector for the table element
        include_headers: Whether to use the table headers as keys (default: True)
        header_selector: Optional custom selector for header cells
        row_selector: Optional custom selector for row elements
        cell_selector: Optional custom selector for cell elements
        parent: Optional parent element to search within

    Returns:
        List of dictionaries, each representing a row of the table
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        page = context.page
        if page is None:
            return Error(Exception("No page found"))

        # Find the table element
        table_element_result = await _find_element_with_parent(context, table_selector, parent)
        if table_element_result.is_error():
            return Error(table_element_result.error)

        table_element = table_element_result.default_value(None)
        if table_element is None:
            return Error(Exception("Table element not found"))

        actual_header_selector = header_selector or "thead th, th"
        actual_row_selector = row_selector or "tbody tr, tr"
        actual_cell_selector = cell_selector or "td"

        table_sel_str = table_element.get_selector()
        if not table_sel_str:
            return Error(Exception("Could not get table selector"))

        headers = []
        if include_headers:
            header_elements_result = await page.query_selector_all(
                f"{table_sel_str} {actual_header_selector}"
            )
            if header_elements_result.is_error():
                return Error(header_elements_result.error)

            header_elements = header_elements_result.default_value(None)
            if header_elements is None:
                return Error(Exception("No header elements found"))

            for header_element in header_elements:
                text_result = await header_element.get_text()
                if text_result.is_error():
                    return Error(text_result.error)

                header_text = text_result.default_value("").strip()
                headers.append(header_text)

        row_elements_result = await page.query_selector_all(
            f"{table_sel_str} {actual_row_selector}"
        )
        if row_elements_result.is_error():
            return Error(row_elements_result.error)

        row_elements = row_elements_result.default_value(None)
        if row_elements is None:
            return Error(Exception("No row elements found"))

        table_data = []
        for row_element in row_elements:
            cell_elements_result = await row_element.query_selector_all(
                actual_cell_selector
            )
            if cell_elements_result.is_error():
                return Error(cell_elements_result.error)

            cell_elements = cell_elements_result.default_value(None)
            if cell_elements is None:
                return Error(Exception("No cell elements found"))

            if not include_headers or not headers:
                row_data = {}
                for i, cell_element in enumerate(cell_elements):
                    text_result = await cell_element.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    cell_text = text_result.default_value("").strip()
                    row_data[f"column_{i}"] = cell_text
            else:
                row_data = {}
                for i, cell_element in enumerate(cell_elements):
                    if i >= len(headers):
                        break

                    text_result = await cell_element.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    cell_text = text_result.default_value("").strip()
                    row_data[headers[i]] = cell_text

            if row_data:
                table_data.append(row_data)

        return Ok(table_data)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def WaitForSelector(
    selector: Union[str, Selector, SelectorGroup],
    options: Optional[WaitOptions] = None,
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[Any, Exception]:
    """
    Action to wait for an element to appear in the DOM

    Args:
        selector: Element selector to wait for
        options: Additional wait options
        parent: Optional parent element to search within

    Returns:
        The found element if successful
    """
    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if context.page_id is None:
            return Error(Exception("No page ID found"))

        # If parent is provided, we need to wait within that parent element
        if parent is not None:
            parent_result = await _resolve_parent(context, parent)
            if parent_result.is_error():
                return Error(parent_result.error)
            
            parent_element = parent_result.default_value(None)
            if parent_element is None:
                return Error(Exception("Parent element not found"))
            
            # Build selector relative to parent
            parent_selector = parent_element.get_selector()
            if not parent_selector:
                return Error(Exception("Could not get parent element selector"))
            
            selector_str = _build_full_selector(parent_selector, selector)
        else:
            # No parent, use selector as is
            selector_str = _get_selector_string(selector)

        # Handle SelectorGroup specially
        if isinstance(selector, SelectorGroup):
            return await _wait_for_selector_group(
                driver, context.page_id, selector, parent_selector if parent else None, options
            )

        result = await driver.wait_for_selector(context.page_id, selector_str, options)
        if result.is_error():
            return Error(result.error)

        return Ok(result.default_value(None))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext) # type: ignore[arg-type]
async def ElementExists(
    selector: Union[str, Selector, SelectorGroup],
    parent: Optional[Union[ElementHandle, str, Selector, SelectorGroup]] = None,
    *,
    context: ActionContext,
) -> Result[bool, Exception]:
    """
    Action to check if an element exists in the DOM

    Args:
        selector: Selector to check for existence
        parent: Optional parent element to search within

    Returns:
        True if the element exists, False otherwise
    """
    try:
        query_result: Result[Optional[ElementHandle], Exception] = await Query(
            selector=selector, 
            parent=parent,
            context=context
        ) # type: ignore[arg-type]
        if query_result.is_error():
            return Ok(False)

        element = query_result.default_value(None)
        return Ok(element is not None)
    except Exception as e:
        return Ok(False)


# Helper functions for WaitForSelector
def _get_selector_string(selector: Union[str, Selector, SelectorGroup]) -> str:
    """Convert selector to string."""
    if isinstance(selector, str):
        return selector
    elif isinstance(selector, Selector):
        return selector.value
    elif isinstance(selector, SelectorGroup):
        # Return first selector for simple case
        return selector.selectors[0].value if selector.selectors else ""
    else:
        raise ValueError(f"Unsupported selector type: {type(selector)}")


def _build_full_selector(parent_selector: str, selector: Union[str, Selector, SelectorGroup]) -> str:
    """Build full selector including parent."""
    if isinstance(selector, str):
        return f"{parent_selector} {selector}"
    elif isinstance(selector, Selector):
        return f"{parent_selector} {selector.value}"
    elif isinstance(selector, SelectorGroup):
        # Return first selector for simple case
        return f"{parent_selector} {selector.selectors[0].value}" if selector.selectors else parent_selector
    else:
        raise ValueError(f"Unsupported selector type: {type(selector)}")


async def _wait_for_selector_group(
    driver: Driver,
    page_id: str,
    selector_group: SelectorGroup,
    parent_selector: Optional[str],
    options: Optional[WaitOptions]
) -> Result[Any, Exception]:
    """Special handling for SelectorGroup in wait operations."""
    selector_promises = []
    for sel in selector_group.selectors:
        if isinstance(sel, str):
            full_sel = f"{parent_selector} {sel}" if parent_selector else sel
            selector_promises.append(f"document.querySelector('{full_sel}')")
        elif isinstance(sel, Selector):
            full_sel = f"{parent_selector} {sel.value}" if parent_selector else sel.value
            selector_promises.append(f"document.querySelector('{full_sel}')")

    if not selector_promises:
        return Error(Exception("Empty selector group"))
    
    function_body = f"""
    () => new Promise((resolve, reject) => {{
        const checkSelectors = () => {{
            const elements = [{", ".join(selector_promises)}].filter(e => e);
            if (elements.length > 0) {{
                resolve(elements[0]);
                return true;
            }}
            return false;
        }};

        if (checkSelectors()) return;

        const observer = new MutationObserver(() => {{
            if (checkSelectors()) observer.disconnect();
        }});

        observer.observe(document.body, {{
            childList: true,
            subtree: true
        }});

        setTimeout(() => {{
            observer.disconnect();
            reject(new Error('Timeout waiting for any selector to appear'));
        }}, {options.timeout if options and options.timeout else 30000});
    }})
    """
    result = await driver.execute_script(page_id, function_body)
    if result.is_error():
        return Error(result.error)

    return Ok(result.default_value(None))