"""
Extraction actions for retrieving data from web pages.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Union

from expression import Error, Ok, Result
from fp_ops import operation

from silk.actions.context import ActionContext
from silk.actions.utils import resolve_target, validate_driver
from silk.browsers.element import ElementHandle
from silk.browsers.types import WaitOptions
from silk.selectors.selector import Selector, SelectorGroup

T = TypeVar("T")
logger = logging.getLogger(__name__)


@operation(context=True, context_type=ActionContext)
async def Query(
    selector: Union[str, Selector, SelectorGroup],
    **kwargs: Any,
) -> Result[Optional[ElementHandle], Exception]:
    """
    Action to query a single element

    Args:
        selector: Selector to find element

    Returns:
        Found element or None if not found
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("No browser page found"))

        if isinstance(selector, str):
            element_result = await page.query_selector(selector)
            if element_result.is_error():
                return Error(element_result.error)
            element = element_result.default_value(None)
            if element is None:
                return Error(Exception("No element found"))
            return Ok(element)

        if isinstance(selector, Selector):
            element_result = await page.query_selector(selector.value)
            if element_result.is_error():
                return Error(element_result.error)
            element = element_result.default_value(None)
            if element is None:
                return Error(Exception("No element found"))
            return Ok(element)

        if isinstance(selector, SelectorGroup):
            for sel in selector.selectors:
                sub_result = await page.query_selector(sel.value)
                if sub_result.is_error():
                    continue
                element = sub_result.default_value(None)
                if element is not None:
                    return Ok(element)
            return Ok(None)

        return Error(Exception(f"Unsupported selector type: {type(selector)}"))
    except Exception as e:
        return Error(e)

@operation(context=True, context_type=ActionContext)
async def QueryAll(
    selector: Union[str, Selector, SelectorGroup],
    **kwargs: Any,
) -> Result[List[ElementHandle], Exception]:
    """
    Action to query multiple elements

    Args:
        selector: Selector to find elements

    Returns:
        List of found elements (empty if none found)
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("No browser page found"))

        if isinstance(selector, str):
            elements_result = await page.query_selector_all(selector)
            if elements_result.is_error():
                return Error(elements_result.error)
            elements = elements_result.default_value(None)
            if elements is None:
                return Error(Exception("No elements found"))
            return Ok(elements)

        if isinstance(selector, Selector):
            elements_result = await page.query_selector_all(selector.value)
            if elements_result.is_error():
                return Error(elements_result.error)
            elements = elements_result.default_value(None)
            if elements is None:
                return Error(Exception("No elements found"))
            return Ok(elements)

        if isinstance(selector, SelectorGroup):
            all_elements = []
            for sel in selector.selectors:
                sub_result = await page.query_selector_all(sel.value)
                if sub_result.is_error():
                    continue
                elements = sub_result.default_value(None)
                if elements is None:
                    continue
                all_elements.extend(elements)
            return Ok(all_elements)

        return Error(Exception(f"Unsupported selector type: {type(selector)}"))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetText(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    **kwargs: Any,
) -> Result[Optional[str], Exception]:
    """
    Action to get text from an element

    Args:
        selector: Selector to find element

    Returns:
        Text content of the element or None if element not found
    """
    context: ActionContext = kwargs["context"]

    try:
        # If we already have an ElementHandle, use it directly
        if isinstance(selector, ElementHandle):
            text_result = await selector.get_text()
            if text_result.is_error():
                return Error(text_result.error)
            text = text_result.default_value("")
            return Ok(text)
            
        # Otherwise, resolve the element using the selector
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        element_result = await resolve_target(context, selector)
        if element_result.is_error():
            return Ok(None)

        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        text_result = await element.get_text()
        if text_result.is_error():
            return Error(text_result.error)

        text = text_result.default_value("")
        return Ok(text)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetAttribute(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    attribute: str,
    **kwargs: Any,
) -> Result[Optional[str], Exception]:
    """
    Action to get an attribute from an element

    Args:
        selector: Selector to find element
        attribute: Attribute name to get

    Returns:
        Attribute value or None if element not found or attribute not present
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        element_result = await resolve_target(context, selector)
        if element_result.is_error():
            return Ok(None)

        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        attr_result = await element.get_attribute(attribute)
        if attr_result.is_error():
            return Error(attr_result.error)

        attr_value = attr_result.default_value(None)
        return Ok(attr_value)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetHtml(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    outer: bool = True,
    **kwargs: Any,
) -> Result[Optional[str], Exception]:
    """
    Action to get HTML content from an element

    Args:
        selector: Selector to find element
        outer: Whether to include the element's outer HTML

    Returns:
        HTML content of the element or None if element not found
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        element_result = await resolve_target(context, selector)
        if element_result.is_error():
            return Ok(None)

        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        html_result = await element.get_html(outer=outer)

        if html_result.is_error():
            return Error(html_result.error)

        html_content = html_result.default_value("")
        return Ok(html_content)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def GetInnerText(
    selector: Union[str, Selector, SelectorGroup, ElementHandle],
    **kwargs: Any,
) -> Result[Optional[str], Exception]:
    """
    Action to get the innerText from an element (visible text only)

    Args:
        selector: Selector to find element

    Returns:
        Inner text of the element or None if element not found
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        element_result = await resolve_target(context, selector)
        if element_result.is_error():
            return Ok(None)

        element = element_result.default_value(None)
        if element is None:
            return Ok(None)

        # Inner text is different from text content - it only includes visible text
        # We need to use evaluate to get it
        if context.page_id is None:
            return Error(Exception("No page ID found"))

        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        selector_str = element.get_selector()
        if not selector_str:
            return Error(Exception("Could not get element selector"))

        js_result = await driver.execute_script(
            context.page_id, f"document.querySelector('{selector_str}').innerText"
        )

        if js_result.is_error():
            return Error(js_result.error)

        inner_text = js_result.default_value("")
        return Ok(inner_text)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def ExtractTable(
    table_selector: Union[str, Selector, SelectorGroup],
    include_headers: bool = True,
    header_selector: Optional[str] = None,
    row_selector: Optional[str] = None,
    cell_selector: Optional[str] = None,
    **kwargs: Any,
) -> Result[List[Dict[str, str]], Exception]:
    """
    Action to extract data from an HTML table

    Args:
        table_selector: Selector for the table element
        include_headers: Whether to use the table headers as keys (default: True)
        header_selector: Optional custom selector for header cells
        row_selector: Optional custom selector for row elements
        cell_selector: Optional custom selector for cell elements

    Returns:
        List of dictionaries, each representing a row of the table
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        page_result = await context.get_page()
        if page_result.is_error():
            return Error(page_result.error)

        page = page_result.default_value(None)
        if page is None:
            return Error(Exception("No browser page found"))

        table_element_result = await resolve_target(context, table_selector)
        if table_element_result.is_error():
            return Error(table_element_result.error)

        table_element = table_element_result.default_value(None)
        if table_element is None:
            return Error(Exception("Table element not found"))

        # Default selectors if not provided
        actual_header_selector = header_selector or "thead th, th"
        actual_row_selector = row_selector or "tbody tr, tr"
        actual_cell_selector = cell_selector or "td"

        # Get the table selector string
        table_sel_str = table_element.get_selector()
        if not table_sel_str:
            return Error(Exception("Could not get table selector"))

        # Get headers if needed
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

        # Get rows
        row_elements_result = await page.query_selector_all(
            f"{table_sel_str} {actual_row_selector}"
        )
        if row_elements_result.is_error():
            return Error(row_elements_result.error)

        row_elements = row_elements_result.default_value(None)
        if row_elements is None:
            return Error(Exception("No row elements found"))

        # Process rows
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

            # If we have no headers, create a simple array row
            if not include_headers or not headers:
                row_data = {}
                for i, cell_element in enumerate(cell_elements):
                    text_result = await cell_element.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    cell_text = text_result.default_value("").strip()
                    row_data[f"column_{i}"] = cell_text
            else:
                # Map cells to headers
                row_data = {}
                for i, cell_element in enumerate(cell_elements):
                    if i >= len(headers):
                        break

                    text_result = await cell_element.get_text()
                    if text_result.is_error():
                        return Error(text_result.error)

                    cell_text = text_result.default_value("").strip()
                    row_data[headers[i]] = cell_text

            if row_data:  # Only add non-empty rows
                table_data.append(row_data)

        return Ok(table_data)
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def WaitForSelector(
    selector: Union[str, Selector, SelectorGroup],
    options: Optional[WaitOptions] = None,
    **kwargs: Any,
) -> Result[Any, Exception]:
    """
    Action to wait for an element to appear in the DOM

    Args:
        selector: Element selector to wait for
        options: Additional wait options

    Returns:
        The found element if successful
    """
    context: ActionContext = kwargs["context"]

    try:
        driver_result = await validate_driver(context)
        if driver_result.is_error():
            return Error(driver_result.error)

        driver = driver_result.default_value(None)
        if driver is None:
            return Error(Exception("No browser driver found"))

        if context.page_id is None:
            return Error(Exception("No page ID found"))

        # Handle different selector types
        selector_str = ""
        if isinstance(selector, str):
            selector_str = selector
        elif isinstance(selector, Selector):
            selector_str = selector.value
        elif isinstance(selector, SelectorGroup):
            # For selector groups, wait for any of the selectors to match
            # This is done by using Promise.race in JavaScript
            selector_promises = []
            for sel in selector.selectors:
                if isinstance(sel, str):
                    selector_promises.append(f"document.querySelector('{sel}')")
                elif isinstance(sel, Selector):
                    selector_promises.append(f"document.querySelector('{sel.value}')")

            if not selector_promises:
                return Error(Exception("Empty selector group"))

            # Create a JavaScript function that resolves when any selector is found
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

            result = await driver.execute_script(context.page_id, function_body)
            if result.is_error():
                return Error(result.error)

            return Ok(result.default_value(None))
        else:
            return Error(Exception(f"Unsupported selector type: {type(selector)}"))

        # For simple selectors, use the driver's wait_for_selector method
        result = await driver.wait_for_selector(context.page_id, selector_str, options)
        if result.is_error():
            return Error(result.error)

        return Ok(result.default_value(None))
    except Exception as e:
        return Error(e)


@operation(context=True, context_type=ActionContext)
async def ElementExists(
    selector: Union[str, Selector, SelectorGroup],
    **kwargs: Any,
) -> Result[bool, Exception]:
    """
    Action to check if an element exists in the DOM

    Args:
        selector: Selector to check for existence

    Returns:
        True if the element exists, False otherwise
    """

    try:
        query_result = await Query(selector, **kwargs)
        if query_result.is_error():
            return Ok(False)

        element = query_result.default_value(None)
        return Ok(element is not None)
    except Exception as e:
        return Ok(False)