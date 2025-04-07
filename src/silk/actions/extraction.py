"""
Extraction actions for retrieving data from web pages.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Union

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.browsers.element import ElementHandle
from silk.models.browser import ActionContext, BrowserPage
from silk.selectors.selector import Selector, SelectorGroup, SelectorType

T = TypeVar("T")
logger = logging.getLogger(__name__)


class Query(Action[Optional[ElementHandle]]):
    """
    Action to query a single element

    Args:
        selector: Selector to find element

    Returns:
        Found element or None if not found
    """

    def __init__(self, selector: Union[str, Selector, SelectorGroup]):
        self.selector = selector

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"

    async def execute(
        self, context: ActionContext
    ) -> Result[Optional[ElementHandle], Exception]:
        """Query a single element"""
        try:
            logger.debug(f"Querying element with selector {self.selector_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        result = await self._query_selector(selector, page)
                        if result.is_ok() and result.default_value(None) is not None:
                            return result
                    except Exception:
                        pass

                return Ok(None)
            else:
                selector = (
                    self.selector
                    if isinstance(self.selector, Selector)
                    else Selector(type=SelectorType.CSS, value=self.selector)
                )
                return await self._query_selector(selector, page)

        except Exception as e:
            logger.error(
                f"Error querying element with selector {self.selector_desc}: {e}"
            )
            return Error(e)

    async def _query_selector(
        self, selector: Selector, page: BrowserPage
    ) -> Result[Optional[ElementHandle], Exception]:
        """Helper method to query a specific selector"""
        try:
            return await page.query_selector(selector.value)
        except Exception as e:
            return Error(e)


class QueryAll(Action[List[ElementHandle]]):
    """
    Action to query multiple elements

    Args:
        selector: Selector to find elements

    Returns:
        List of found elements (empty if none found)
    """

    def __init__(self, selector: Union[str, Selector, SelectorGroup]):
        self.selector = selector

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"

    async def execute(
        self, context: ActionContext
    ) -> Result[List[ElementHandle], Exception]:
        """Query multiple elements"""
        try:
            logger.debug(f"Querying all elements with selector {self.selector_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    result = await self._query_selector_all(selector, page)
                    if result.is_ok() and len(result.default_value([])) > 0:
                        return result

                return Ok([])
            else:
                selector = (
                    self.selector
                    if isinstance(self.selector, Selector)
                    else Selector(type=SelectorType.CSS, value=self.selector)
                )
                return await self._query_selector_all(selector, page)

        except Exception as e:
            logger.error(
                f"Error querying elements with selector {self.selector_desc}: {e}"
            )
            return Error(e)

    async def _query_selector_all(
        self, selector: Selector, page: BrowserPage
    ) -> Result[List[ElementHandle], Exception]:
        """Helper method to query a specific selector"""
        try:
            return await page.query_selector_all(selector.value)
        except Exception as e:
            return Error(e)


class GetText(Action[str]):
    """
    Action to get text from an element

    Args:
        selector: Selector to find element

    Returns:
        Text content of the element
    """

    def __init__(self, selector: Union[str, Selector, SelectorGroup, ElementHandle]):
        self.selector = selector

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        """Get text from element"""
        try:
            logger.debug(
                f"Getting text from element with selector {self.selector_desc}"
            )

            if isinstance(self.selector, ElementHandle):
                return await self.selector.get_text()

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        result = await self._get_text_from_selector(selector, page)
                        if result.is_ok():
                            return result
                    except Exception:
                        pass

                return Error(
                    Exception(
                        f"Failed to get text from any selector in group: {self.selector.name}"
                    )
                )
            else:
                selector = (
                    self.selector
                    if isinstance(self.selector, Selector)
                    else Selector(type=SelectorType.CSS, value=self.selector)
                )
                return await self._get_text_from_selector(selector, page)

        except Exception as e:
            logger.error(
                f"Error getting text from element with selector {self.selector_desc}: {e}"
            )
            return Error(e)

    async def _get_text_from_selector(
        self, selector: Selector, page: BrowserPage
    ) -> Result[str, Exception]:
        """Helper method to get text from a specific selector"""
        try:
            element_result = await page.query_selector(selector.value)
            if element_result.is_error():
                return Error(element_result.error)

            element = element_result.default_value(None)
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))

            return await element.get_text()
        except Exception as e:
            return Error(e)


class GetAttribute(Action[Optional[str]]):
    """
    Action to get an attribute from an element

    Args:
        selector: Selector to find element
        attribute: Attribute name to get

    Returns:
        Attribute value or None if not found
    """

    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup, ElementHandle],
        attribute: str,
    ):
        self.selector = selector
        self.attribute = attribute

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[Optional[str], Exception]:
        """Get attribute from element"""
        try:
            logger.debug(
                f"Getting attribute '{self.attribute}' from element with selector {self.selector_desc}"
            )

            if isinstance(self.selector, ElementHandle):
                return await self.selector.get_attribute(self.attribute)

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        result = await self._get_attribute_from_selector(selector, page)
                        if result.is_ok():
                            return result
                    except Exception:
                        pass

                return Error(
                    Exception(
                        f"Failed to get attribute from any selector in group: {self.selector.name}"
                    )
                )
            else:
                selector = (
                    self.selector
                    if isinstance(self.selector, Selector)
                    else Selector(type=SelectorType.CSS, value=self.selector)
                )
                return await self._get_attribute_from_selector(selector, page)

        except Exception as e:
            logger.error(
                f"Error getting attribute '{self.attribute}' from element with selector {self.selector_desc}: {e}"
            )
            return Error(e)

    async def _get_attribute_from_selector(
        self, selector: Selector, page: BrowserPage
    ) -> Result[Optional[str], Exception]:
        """Helper method to get attribute from a specific selector"""
        try:
            element_result = await page.query_selector(selector.value)
            if element_result.is_error():
                return Error(element_result.error)

            element = element_result.default_value(None)
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))

            return await element.get_attribute(self.attribute)
        except Exception as e:
            return Error(e)


class GetHtml(Action[str]):
    """
    Action to get HTML content from an element

    Args:
        selector: Selector to find element
        outer: Whether to include the element's outer HTML

    Returns:
        HTML content of the element
    """

    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup, ElementHandle],
        outer: bool = True,
    ):
        self.selector = selector
        self.outer = outer

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        """Get HTML from element"""
        try:
            logger.debug(
                f"Getting {'outer' if self.outer else 'inner'}HTML from element with selector {self.selector_desc}"
            )

            if isinstance(self.selector, ElementHandle):
                return await self.selector.get_html(self.outer)

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        element_result = await page.query_selector(selector.value)
                        if element_result.is_error():
                            continue

                        element = element_result.default_value(None)
                        if element is None:
                            continue

                        html_result = await element.get_html(self.outer)
                        if html_result.is_ok():
                            return html_result
                    except Exception:
                        pass

                return Error(
                    Exception(f"No selector in group matched: {self.selector.name}")
                )
            else:
                selector_value = (
                    self.selector.value
                    if isinstance(self.selector, Selector)
                    else self.selector
                )

                element_result = await page.query_selector(selector_value)
                if element_result.is_error():
                    return Error(element_result.error)

                element = element_result.default_value(None)
                if element is None:
                    return Error(Exception(f"Element not found: {self.selector_desc}"))

                return await element.get_html(self.outer)
        except Exception as e:
            logger.error(
                f"Error getting HTML from element with selector {self.selector_desc}: {e}"
            )
            return Error(e)


class GetInnerText(Action[str]):
    """
    Action to get the innerText from an element (visible text only)

    Args:
        selector: Selector to find element

    Returns:
        Inner text of the element
    """

    def __init__(self, selector: Union[str, Selector, SelectorGroup, ElementHandle]):
        self.selector = selector

        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"

    async def execute(self, context: ActionContext) -> Result[str, Exception]:
        """Get inner text from element"""
        try:
            logger.debug(
                f"Getting innerText from element with selector {self.selector_desc}"
            )

            if isinstance(self.selector, ElementHandle):
                return await self.selector.get_inner_text()

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.selector, SelectorGroup):
                for selector in self.selector.selectors:
                    try:
                        element_result = await page.query_selector(selector.value)
                        if element_result.is_error():
                            continue

                        element = element_result.default_value(None)
                        if element is None:
                            continue

                        inner_text_result = await element.get_inner_text()
                        if inner_text_result.is_ok():
                            return inner_text_result
                    except Exception:
                        pass

                return Error(
                    Exception(f"No selector in group matched: {self.selector.name}")
                )
            else:
                selector_value = (
                    self.selector.value
                    if isinstance(self.selector, Selector)
                    else self.selector
                )

                element_result = await page.query_selector(selector_value)
                if element_result.is_error():
                    return Error(element_result.error)

                element = element_result.default_value(None)
                if element is None:
                    return Error(Exception(f"Element not found: {self.selector_desc}"))

                return await element.get_inner_text()
        except Exception as e:
            logger.error(
                f"Error getting innerText from element with selector {self.selector_desc}: {e}"
            )
            return Error(e)


class Evaluate(Action[Any]):
    """
    Action to evaluate JavaScript in context of the page

    Args:
        script: JavaScript code to evaluate
        *args: Arguments to pass to the script

    Returns:
        Result of the evaluation
    """

    def __init__(self, script: str, *args: Any):
        self.script = script
        self.args = args

    async def execute(self, context: ActionContext) -> Result[Any, Exception]:
        """Evaluate JavaScript code"""
        try:
            logger.debug(f"Evaluating JavaScript: {self.script[:50]}...")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            return await page.execute_script(self.script, *self.args)
        except Exception as e:
            logger.error(f"Error evaluating JavaScript: {e}")
            return Error(e)


class ExtractTable(Action[List[Dict[str, str]]]):
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

    def __init__(
        self,
        table_selector: Union[str, Selector, SelectorGroup],
        include_headers: bool = True,
        header_selector: Optional[str] = None,
        row_selector: Optional[str] = None,
        cell_selector: Optional[str] = None,
    ):
        self.table_selector = table_selector
        self.include_headers = include_headers
        self.header_selector = header_selector or "th"
        self.row_selector = row_selector or "tr"
        self.cell_selector = cell_selector or "td"

        if isinstance(table_selector, str):
            self.selector_desc = f"'{table_selector}'"
        elif isinstance(table_selector, Selector):
            self.selector_desc = f"{table_selector}"
        else:
            self.selector_desc = f"selector group '{table_selector.name}'"

    async def execute(
        self, context: ActionContext
    ) -> Result[List[Dict[str, str]], Exception]:
        """Extract table data to list of dictionaries"""
        try:
            logger.debug(f"Extracting data from table {self.selector_desc}")

            page_result = await context.get_page()
            if page_result.is_error():
                return Error(page_result.error)

            page = page_result.default_value(None)
            if page is None:
                return Error(Exception("Failed to get page from context"))

            if isinstance(self.table_selector, SelectorGroup):
                for selector in self.table_selector.selectors:
                    table_element_result = await page.query_selector(selector.value)
                    if table_element_result.is_error():
                        continue

                    table_element = table_element_result.default_value(None)
                    if table_element is None:
                        continue

                    result = await page.driver.extract_table(
                        page.id,
                        table_element,
                        include_headers=self.include_headers,
                        header_selector=self.header_selector,
                        row_selector=self.row_selector,
                        cell_selector=self.cell_selector,
                    )
                    value: List[Dict[str, str]] = result.default_value([])
                    if result.is_ok() and value is not None:
                        return Ok(value)

                return Error(
                    Exception(
                        f"No selector in group matched a table: {self.table_selector.name}"
                    )
                )
            else:
                if isinstance(self.table_selector, Selector):
                    selector_value = self.table_selector.value
                else:
                    selector_value = self.table_selector

                table_element_result = await page.query_selector(selector_value)
                if table_element_result.is_error():
                    return Error(table_element_result.error)

                table_element = table_element_result.default_value(None)
                if table_element is None:
                    return Error(
                        Exception(f"Table element not found: {self.selector_desc}")
                    )

                result = await page.driver.extract_table(
                    page.id,
                    table_element,
                    include_headers=self.include_headers,
                    header_selector=self.header_selector,
                    row_selector=self.row_selector,
                    cell_selector=self.cell_selector,
                )
                table_data: List[Dict[str, str]] = result.default_value([])
                if result.is_ok() and table_data is not None:
                    return Ok(table_data)

                return Error(Exception(f"Failed to extract table data: {result.error}"))
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return Error(e)
