"""
Extraction actions for retrieving data from web pages.
"""

from typing import Optional, Union, List, Dict, Any, TypeVar, Generic, cast
from expression.core import Result, Ok, Error
import logging

from silk.browsers.driver import BrowserDriver
from silk.models.browser import ActionContext, ElementHandle
from silk.actions.base import Action
from silk.selectors.selector import Selector, SelectorGroup

T = TypeVar('T')
logger = logging.getLogger(__name__)


class Query(Action[Optional[ElementHandle]]):
    """
    Action to query a single element
    
    Args:
        selector: Selector to find element
        
    Returns:
        Found element or None if not found
    """
    
    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup]
    ):
        self.selector = selector
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Optional[ElementHandle], Exception]:
        """Query a single element"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Querying element with selector {self.selector_desc}")
            
            if isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                return await self.selector.execute(
                    lambda selector: self._query_selector(driver, selector)
                )
            else:
                # Convert string to Selector if needed
                selector = self.selector if isinstance(self.selector, Selector) else Selector(
                    type="css", value=self.selector
                )
                return await self._query_selector(driver, selector)
                
        except Exception as e:
            logger.error(f"Error querying element with selector {self.selector_desc}: {e}")
            return Error(e)
    
    async def _query_selector(self, driver: BrowserDriver, selector: Selector) -> Result[Optional[ElementHandle], Exception]:
        """Helper method to query a specific selector"""
        try:
            # Handle different selector types
            if selector.type == "css":
                return await driver.query_selector(selector.value)
            elif selector.type == "xpath":
                # Some drivers may have special handling for XPath
                return await driver.query_selector(selector.value)
            else:
                # For other selector types, convert to appropriate format
                # This is a simplification - real implementation would handle all types
                return await driver.query_selector(selector.value)
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
    
    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup]
    ):
        self.selector = selector
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[List[ElementHandle], Exception]:
        """Query multiple elements"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Querying all elements with selector {self.selector_desc}")
            
            if isinstance(self.selector, SelectorGroup):
                # Try each selector in the group until one works
                all_results = []
                for selector in self.selector.selectors:
                    result = await self._query_selector_all(driver, selector)
                    if result.is_ok() and result.value:  # If we found elements
                        return result
                    
                # If we get here, return the last result (likely empty list)
                return result
            else:
                # Convert string to Selector if needed
                selector = self.selector if isinstance(self.selector, Selector) else Selector(
                    type="css", value=self.selector
                )
                return await self._query_selector_all(driver, selector)
                
        except Exception as e:
            logger.error(f"Error querying elements with selector {self.selector_desc}: {e}")
            return Error(e)
    
    async def _query_selector_all(self, driver: BrowserDriver, selector: Selector) -> Result[List[ElementHandle], Exception]:
        """Helper method to query a specific selector"""
        try:
            # Handle different selector types
            if selector.type == "css":
                return await driver.query_selector_all(selector.value)
            elif selector.type == "xpath":
                # Some drivers may have special handling for XPath
                return await driver.query_selector_all(selector.value)
            else:
                # For other selector types, convert to appropriate format
                return await driver.query_selector_all(selector.value)
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
    
    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup, ElementHandle]
    ):
        self.selector = selector
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Get text from element"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Getting text from element with selector {self.selector_desc}")
            
            if isinstance(self.selector, ElementHandle):
                # Get text directly from element handle
                return await self.selector.get_text()
            elif isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                return await self.selector.execute(
                    lambda selector: self._get_text_from_selector(driver, selector)
                )
            else:
                # Convert string to Selector if needed
                selector = self.selector if isinstance(self.selector, Selector) else Selector(
                    type="css", value=self.selector
                )
                return await self._get_text_from_selector(driver, selector)
                
        except Exception as e:
            logger.error(f"Error getting text from element with selector {self.selector_desc}: {e}")
            return Error(e)
    
    async def _get_text_from_selector(self, driver: BrowserDriver, selector: Selector) -> Result[str, Exception]:
        """Helper method to get text from a specific selector"""
        try:
            # Get element
            result = await driver.query_selector(selector.value)
            if result.is_error():
                return Error(Exception(f"Failed to query selector: {selector}"))
                
            element = result.value
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))
                
            # Get text
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
        attribute: str
    ):
        self.selector = selector
        self.attribute = attribute
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Optional[str], Exception]:
        """Get attribute from element"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Getting attribute '{self.attribute}' from element with selector {self.selector_desc}")
            
            if isinstance(self.selector, ElementHandle):
                # Get attribute directly from element handle
                return await self.selector.get_attribute(self.attribute)
            elif isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                return await self.selector.execute(
                    lambda selector: self._get_attribute_from_selector(driver, selector)
                )
            else:
                # Convert string to Selector if needed
                selector = self.selector if isinstance(self.selector, Selector) else Selector(
                    type="css", value=self.selector
                )
                return await self._get_attribute_from_selector(driver, selector)
                
        except Exception as e:
            logger.error(f"Error getting attribute '{self.attribute}' from element with selector {self.selector_desc}: {e}")
            return Error(e)
    
    async def _get_attribute_from_selector(self, driver: BrowserDriver, selector: Selector) -> Result[Optional[str], Exception]:
        """Helper method to get attribute from a specific selector"""
        try:
            # Get element
            result = await driver.query_selector(selector.value)
            if result.is_error():
                return Error(Exception(f"Failed to query selector: {selector}"))
                
            element = result.value
            if element is None:
                return Error(Exception(f"Element not found: {selector}"))
                
            # Get attribute
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
        outer: bool = True
    ):
        self.selector = selector
        self.outer = outer
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Get HTML from element"""
        ctx = context or ActionContext()
        
        try:
            html_type = "outerHTML" if self.outer else "innerHTML"
            logger.debug(f"Getting {html_type} from element with selector {self.selector_desc}")
            
            # Use JavaScript to get HTML content
            script = f"""
                const element = arguments[0];
                return element ? element.{html_type} : null;
            """
            
            if isinstance(self.selector, ElementHandle):
                # Use JavaScript to get HTML from element handle
                # We need to find a way to pass the element to JavaScript
                # This is a limitation in many browser drivers
                
                # Get bounding box to identify the element
                bbox_result = await self.selector.get_bounding_box()
                if bbox_result.is_error():
                    return Error(Exception(f"Cannot get element position: {bbox_result.error}"))
                
                # Use elementFromPoint as a workaround
                complex_script = f"""
                    const elem = document.elementFromPoint({bbox_result.value['x']}, {bbox_result.value['y']});
                    return elem ? elem.{html_type} : null;
                """
                
                result = await driver.execute_script(complex_script)
            elif isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                for selector in self.selector.selectors:
                    result = await driver.execute_script(
                        f"const element = document.querySelector('{selector.value}'); {script.split('arguments[0]')[1]}"
                    )
                    
                    if result.is_ok() and result.value:
                        return result
                        
                return Error(Exception(f"No selector in group matched: {self.selector.name}"))
            else:
                # Convert string to selector value if needed
                selector_value = self.selector.value if isinstance(self.selector, Selector) else self.selector
                
                # Get element and its HTML
                selector_script = f"""
                    const element = document.querySelector('{selector_value}');
                    {script.split('arguments[0]')[1]}
                """
                
                result = await driver.execute_script(selector_script)
            
            if result.is_error():
                return result
                
            if result.value is None:
                return Error(Exception(f"Element not found: {self.selector_desc}"))
                
            return Ok(str(result.value))
        except Exception as e:
            logger.error(f"Error getting HTML from element with selector {self.selector_desc}: {e}")
            return Error(e)


class GetInnerText(Action[str]):
    """
    Action to get the innerText from an element (visible text only)
    
    Args:
        selector: Selector to find element
        
    Returns:
        Inner text of the element
    """
    
    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup, ElementHandle]
    ):
        self.selector = selector
        
        # Generate description for logging
        if isinstance(selector, str):
            self.selector_desc = f"'{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        elif isinstance(selector, SelectorGroup):
            self.selector_desc = f"selector group '{selector.name}'"
        else:
            self.selector_desc = "element handle"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[str, Exception]:
        """Get inner text from element"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Getting innerText from element with selector {self.selector_desc}")
            
            # Use JavaScript to get innerText content
            script = """
                const element = arguments[0];
                return element ? element.innerText : null;
            """
            
            # Use similar approach as GetHtml
            if isinstance(self.selector, ElementHandle):
                bbox_result = await self.selector.get_bounding_box()
                if bbox_result.is_error():
                    return Error(Exception(f"Cannot get element position: {bbox_result.error}"))
                
                complex_script = """
                    const elem = document.elementFromPoint(arguments[0], arguments[1]);
                    return elem ? elem.innerText : null;
                """
                
                result = await driver.execute_script(
                    complex_script, 
                    bbox_result.value['x'], 
                    bbox_result.value['y']
                )
            elif isinstance(self.selector, SelectorGroup):
                # Try each selector in the group
                for selector in self.selector.selectors:
                    selector_script = f"""
                        const element = document.querySelector('{selector.value}');
                        return element ? element.innerText : null;
                    """
                    
                    result = await driver.execute_script(selector_script)
                    
                    if result.is_ok() and result.value:
                        return Ok(str(result.value))
                        
                return Error(Exception(f"No selector in group matched: {self.selector.name}"))
            else:
                # Convert string to selector value if needed
                selector_value = self.selector.value if isinstance(self.selector, Selector) else self.selector
                
                selector_script = f"""
                    const element = document.querySelector('{selector_value}');
                    return element ? element.innerText : null;
                """
                
                result = await driver.execute_script(selector_script)
            
            if result.is_error():
                return result
                
            if result.value is None:
                return Error(Exception(f"Element not found: {self.selector_desc}"))
                
            return Ok(str(result.value))
        except Exception as e:
            logger.error(f"Error getting innerText from element with selector {self.selector_desc}: {e}")
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
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[Any, Exception]:
        """Evaluate JavaScript code"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Evaluating JavaScript: {self.script[:50]}...")
            return await driver.execute_script(self.script, *self.args)
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
        cell_selector: Optional[str] = None
    ):
        self.table_selector = table_selector
        self.include_headers = include_headers
        self.header_selector = header_selector or "th"
        self.row_selector = row_selector or "tr"
        self.cell_selector = cell_selector or "td"
        
        # Generate description for logging
        if isinstance(table_selector, str):
            self.selector_desc = f"'{table_selector}'"
        elif isinstance(table_selector, Selector):
            self.selector_desc = f"{table_selector}"
        else:
            self.selector_desc = f"selector group '{table_selector.name}'"
    
    async def execute(self, driver: BrowserDriver, context: Optional[ActionContext] = None) -> Result[List[Dict[str, str]], Exception]:
        """Extract table data to list of dictionaries"""
        ctx = context or ActionContext()
        
        try:
            logger.debug(f"Extracting data from table {self.selector_desc}")
            
            # Use JavaScript to extract table data
            script = """
                function extractTable() {
                    const table = document.querySelector(arguments[0]);
                    if (!table) return { error: 'Table not found' };
                    
                    const includeHeaders = arguments[1];
                    const headerSelector = arguments[2];
                    const rowSelector = arguments[3];
                    const cellSelector = arguments[4];
                    
                    // Extract headers
                    let headers = [];
                    if (includeHeaders) {
                        headers = Array.from(table.querySelectorAll(headerSelector)).map(
                            header => header.textContent.trim()
                        );
                        
                        // If no explicit headers found, try first row
                        if (headers.length === 0) {
                            const firstRow = table.querySelector(rowSelector);
                            if (firstRow) {
                                headers = Array.from(firstRow.querySelectorAll(cellSelector)).map(
                                    cell => cell.textContent.trim()
                                );
                            }
                        }
                        
                        // If still no headers, use column indices
                        if (headers.length === 0) {
                            const firstRow = table.querySelector(rowSelector);
                            if (firstRow) {
                                const cellCount = firstRow.querySelectorAll(cellSelector).length;
                                headers = Array.from({ length: cellCount }, (_, i) => `Column ${i + 1}`);
                            }
                        }
                    }
                    
                    // Extract rows
                    const rows = Array.from(table.querySelectorAll(rowSelector));
                    
                    // Skip first row if using headers and no explicit headers found
                    const startIndex = (includeHeaders && table.querySelectorAll(headerSelector).length === 0) ? 1 : 0;
                    
                    // Process each row
                    const result = [];
                    for (let i = startIndex; i < rows.length; i++) {
                        const row = rows[i];
                        const cells = Array.from(row.querySelectorAll(cellSelector)).map(
                            cell => cell.textContent.trim()
                        );
                        
                        if (cells.length === 0) continue; // Skip empty rows
                        
                        if (includeHeaders) {
                            // Create object with headers as keys
                            const rowData = {};
                            cells.forEach((cell, index) => {
                                const key = index < headers.length ? headers[index] : `Column ${index + 1}`;
                                rowData[key] = cell;
                            });
                            result.push(rowData);
                        } else {
                            // Just use array of values
                            result.push(cells.reduce((obj, cell, index) => {
                                obj[`Column ${index + 1}`] = cell;
                                return obj;
                            }, {}));
                        }
                    }
                    
                    return { data: result };
                }
                
                return extractTable();
            """
            
            # Get selector value
            if isinstance(self.table_selector, SelectorGroup):
                # Try each selector in the group
                for selector in self.table_selector.selectors:
                    result = await driver.execute_script(
                        script,
                        selector.value,
                        self.include_headers,
                        self.header_selector,
                        self.row_selector,
                        self.cell_selector
                    )
                    
                    if result.is_ok() and "data" in result.value:
                        return Ok(result.value["data"])
                        
                return Error(Exception(f"No selector in group matched a table: {self.table_selector.name}"))
            else:
                # Get selector value
                selector_value = getattr(self.table_selector, "value", self.table_selector)
                
                result = await driver.execute_script(
                    script,
                    selector_value,
                    self.include_headers,
                    self.header_selector,
                    self.row_selector,
                    self.cell_selector
                )
            
            if result.is_error():
                return result
                
            if "error" in result.value:
                return Error(Exception(result.value["error"]))
                
            return Ok(result.value["data"])
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return Error(e)