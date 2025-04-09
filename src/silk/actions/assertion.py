"""
Assertion actions for validating conditions in browser tests.
"""

import logging
from typing import Any, Callable, List, Optional, Union

from expression.core import Error, Ok, Result

from silk.actions.base import Action
from silk.browsers.element import ElementHandle
from silk.models.browser import ActionContext
from silk.selectors.selector import Selector, SelectorGroup, SelectorType

logger = logging.getLogger(__name__)


class Assert(Action[bool]):
    """
    Base action for all assertions that validates a condition and returns a boolean result

    Args:
        message: Custom error message to show when assertion fails
    """

    def __init__(self, message: Optional[str] = None):
        self.message = message

    async def execute(self, context: ActionContext) -> Result[bool, Exception]:
        """
        Execute the assertion using the given context

        Args:
            context: Execution context with references to browser and page

        Returns:
            Result containing True if assertion passed or an Exception if it failed
        """
        try:
            is_valid = await self._validate(context)
            if is_valid:
                return Ok(True)
            else:
                error_msg = self.message or self._get_default_error_message()
                return Error(AssertionError(error_msg))
        except Exception as e:
            logger.error(f"Error during assertion validation: {e}")
            return Error(e)
    
    async def _validate(self, context: ActionContext) -> bool:
        """
        Validate if the assertion condition is true

        Args:
            context: Execution context with references to browser and page

        Returns:
            True if the assertion passes, False otherwise
        """
        raise NotImplementedError("Subclasses must implement _validate")
    
    def _get_default_error_message(self) -> str:
        """Get the default error message if none was provided"""
        return "Assertion failed"


class AssertElementExists(Assert):
    """
    Assert that an element exists in the page

    Args:
        target: Target selector or element to check
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.target = target

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the element exists"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        if isinstance(self.target, ElementHandle):
            return True  # Element handle already exists
        elif isinstance(self.target, SelectorGroup):
            for selector in self.target.selectors:
                element_result = await page.query_selector(selector.value)
                if element_result.is_ok():
                    element = element_result.default_value(None)
                    if element is not None:
                        return True
            return False
        else:
            selector_value = (
                self.target.value
                if isinstance(self.target, Selector)
                else self.target
            )
            element_result = await page.query_selector(selector_value)
            if element_result.is_error():
                return False
            
            element = element_result.default_value(None)
            return element is not None

    def _get_default_error_message(self) -> str:
        return f"Element with {self.target_desc} does not exist"


class AssertElementVisible(Assert):
    """
    Assert that an element is visible in the page

    Args:
        target: Target selector or element to check
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.target = target

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the element is visible"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        if isinstance(self.target, ElementHandle):
            visibility_result = await self.target.is_visible()
            if visibility_result.is_error():
                return False
            return visibility_result.default_value(False)
        elif isinstance(self.target, SelectorGroup):
            for selector in self.target.selectors:
                element_result = await page.query_selector(selector.value)
                if element_result.is_error():
                    continue
                
                element = element_result.default_value(None)
                if element is None:
                    continue
                
                visibility_result = await element.is_visible()
                if visibility_result.is_error():
                    continue
                
                if visibility_result.default_value(False):
                    return True
            
            return False
        else:
            selector_value = (
                self.target.value
                if isinstance(self.target, Selector)
                else self.target
            )
            element_result = await page.query_selector(selector_value)
            if element_result.is_error():
                return False
            
            element = element_result.default_value(None)
            if element is None:
                return False
            
            visibility_result = await element.is_visible()
            if visibility_result.is_error():
                return False
            
            return visibility_result.default_value(False)

    def _get_default_error_message(self) -> str:
        return f"Element with {self.target_desc} is not visible"


class AssertElementHasText(Assert):
    """
    Assert that an element contains specific text

    Args:
        target: Target selector or element to check
        text: Text that should be present in the element
        exact: Whether the text should match exactly or just be contained
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        text: str,
        exact: bool = False,
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.target = target
        self.text = text
        self.exact = exact

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the element has the expected text"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        if isinstance(self.target, ElementHandle):
            text_result = await self.target.get_text()
            if text_result.is_error():
                return False
            
            element_text = text_result.default_value("")
            return self._text_matches(element_text)
        elif isinstance(self.target, SelectorGroup):
            for selector in self.target.selectors:
                element_result = await page.query_selector(selector.value)
                if element_result.is_error():
                    continue
                
                element = element_result.default_value(None)
                if element is None:
                    continue
                
                text_result = await element.get_text()
                if text_result.is_error():
                    continue
                
                element_text = text_result.default_value("")
                if self._text_matches(element_text):
                    return True
            
            return False
        else:
            selector_value = (
                self.target.value
                if isinstance(self.target, Selector)
                else self.target
            )
            element_result = await page.query_selector(selector_value)
            if element_result.is_error():
                return False
            
            element = element_result.default_value(None)
            if element is None:
                return False
            
            text_result = await element.get_text()
            if text_result.is_error():
                return False
            
            element_text = text_result.default_value("")
            return self._text_matches(element_text)

    def _text_matches(self, element_text: str) -> bool:
        """Check if the element text matches the expected text"""
        if self.exact:
            return element_text == self.text
        else:
            return self.text in element_text

    def _get_default_error_message(self) -> str:
        match_type = "exactly match" if self.exact else "contain"
        return f"Element with {self.target_desc} does not {match_type} text '{self.text}'"


class AssertElementHasAttribute(Assert):
    """
    Assert that an element has a specific attribute with an optional value

    Args:
        target: Target selector or element to check
        attribute: Name of the attribute to check
        value: Optional value the attribute should have
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        target: Union[str, Selector, SelectorGroup, ElementHandle],
        attribute: str,
        value: Optional[str] = None,
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.target = target
        self.attribute = attribute
        self.value = value

        if isinstance(target, str):
            self.target_desc = f"selector '{target}'"
        elif isinstance(target, Selector):
            self.target_desc = f"{target}"
        elif isinstance(target, SelectorGroup):
            self.target_desc = f"selector group '{target.name}'"
        else:
            self.target_desc = "element handle"

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the element has the specified attribute with the expected value"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        if isinstance(self.target, ElementHandle):
            attr_result = await self.target.get_attribute(self.attribute)
            if attr_result.is_error():
                return False
            
            attr_value = attr_result.default_value(None)
            return self._attribute_matches(attr_value)
        elif isinstance(self.target, SelectorGroup):
            for selector in self.target.selectors:
                element_result = await page.query_selector(selector.value)
                if element_result.is_error():
                    continue
                
                element = element_result.default_value(None)
                if element is None:
                    continue
                
                attr_result = await element.get_attribute(self.attribute)
                if attr_result.is_error():
                    continue
                
                attr_value = attr_result.default_value(None)
                if self._attribute_matches(attr_value):
                    return True
            
            return False
        else:
            selector_value = (
                self.target.value
                if isinstance(self.target, Selector)
                else self.target
            )
            element_result = await page.query_selector(selector_value)
            if element_result.is_error():
                return False
            
            element = element_result.default_value(None)
            if element is None:
                return False
            
            attr_result = await element.get_attribute(self.attribute)
            if attr_result.is_error():
                return False
            
            attr_value = attr_result.default_value(None)
            return self._attribute_matches(attr_value)

    def _attribute_matches(self, attr_value: Optional[str]) -> bool:
        """Check if the attribute exists and matches the expected value"""
        if attr_value is None:
            return False
        
        if self.value is None:
            return True  # Only checking for attribute existence
        
        return attr_value == self.value

    def _get_default_error_message(self) -> str:
        if self.value is None:
            return f"Element with {self.target_desc} does not have the attribute '{self.attribute}'"
        else:
            return f"Element with {self.target_desc} does not have attribute '{self.attribute}' with value '{self.value}'"


class AssertElementCount(Assert):
    """
    Assert that a specific number of elements matching a selector exist

    Args:
        selector: Selector to count elements for
        count: Expected count of elements
        operator: Comparison operator ('=', '>', '<', '>=', '<=', '!=')
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        selector: Union[str, Selector, SelectorGroup],
        count: int,
        operator: str = "=",
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.selector = selector
        self.count = count
        self.operator = operator

        if operator not in ["=", ">", "<", ">=", "<=", "!="]:
            raise ValueError(f"Invalid operator: {operator}")

        if isinstance(selector, str):
            self.selector_desc = f"selector '{selector}'"
        elif isinstance(selector, Selector):
            self.selector_desc = f"{selector}"
        else:
            self.selector_desc = f"selector group '{selector.name}'"

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the number of elements matches the expected count"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        if isinstance(self.selector, SelectorGroup):
            # For selector groups, we need to count each selector and sum them
            total_count = 0
            for selector in self.selector.selectors:
                count_result = await self._count_elements(selector.value, page)
                if count_result.is_error():
                    return False
                
                total_count += count_result.default_value(0)
            
            return self._compare_count(total_count)
        else:
            selector_value = (
                self.selector.value
                if isinstance(self.selector, Selector)
                else self.selector
            )
            count_result = await self._count_elements(selector_value, page)
            if count_result.is_error():
                return False
            
            actual_count = count_result.default_value(0)
            return self._compare_count(actual_count)

    async def _count_elements(self, selector: str, page: Any) -> Result[int, Exception]:
        """Count elements matching a selector"""
        try:
            elements_result = await page.query_selector_all(selector)
            if elements_result.is_error():
                return Error(elements_result.error)
            
            elements = elements_result.default_value([])
            return Ok(len(elements))
        except Exception as e:
            return Error(e)

    def _compare_count(self, actual_count: int) -> bool:
        """Compare the actual count with the expected count using the specified operator"""
        if self.operator == "=":
            return actual_count == self.count
        elif self.operator == ">":
            return actual_count > self.count
        elif self.operator == "<":
            return actual_count < self.count
        elif self.operator == ">=":
            return actual_count >= self.count
        elif self.operator == "<=":
            return actual_count <= self.count
        elif self.operator == "!=":
            return actual_count != self.count
        return False

    def _get_default_error_message(self) -> str:
        return f"Expected {self.selector_desc} to have {self.operator} {self.count} elements"


class AssertURL(Assert):
    """
    Assert that the current page URL matches an expected pattern

    Args:
        url: Expected URL or URL pattern
        exact: Whether the URL should match exactly or just contain the pattern
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        url: str,
        exact: bool = False,
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.url = url
        self.exact = exact

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the current page URL matches the expected URL"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        url_result = await page.get_url()
        if url_result.is_error():
            return False
        
        current_url = url_result.default_value("")
        
        if self.exact:
            return current_url == self.url
        else:
            return self.url in current_url

    def _get_default_error_message(self) -> str:
        match_type = "exactly match" if self.exact else "contain"
        return f"Current URL does not {match_type} '{self.url}'"


class AssertTitle(Assert):
    """
    Assert that the current page title matches an expected pattern

    Args:
        title: Expected title or title pattern
        exact: Whether the title should match exactly or just contain the pattern
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        title: str,
        exact: bool = False,
        message: Optional[str] = None,
    ):
        super().__init__(message)
        self.title = title
        self.exact = exact

    async def _validate(self, context: ActionContext) -> bool:
        """Check if the current page title matches the expected title"""
        page_result = await context.get_page()
        if page_result.is_error():
            return False

        page = page_result.default_value(None)
        if page is None:
            return False

        title_result = await page.get_title()
        if title_result.is_error():
            return False
        
        current_title = title_result.default_value("")
        
        if self.exact:
            return current_title == self.title
        else:
            return self.title in current_title

    def _get_default_error_message(self) -> str:
        match_type = "exactly match" if self.exact else "contain"
        return f"Current page title does not {match_type} '{self.title}'"


class AssertCondition(Assert):
    """
    Custom assertion that evaluates a condition with an optional message

    Args:
        condition: A callable that will be evaluated to determine if the assertion passes
        message: Custom error message to show when assertion fails
    """

    def __init__(
        self,
        condition: Callable[[ActionContext], bool],
        message: Optional[str] = None,
    ):
        super().__init__(message or "Custom condition failed")
        self.condition = condition

    async def _validate(self, context: ActionContext) -> bool:
        """Evaluate the custom condition"""
        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Error evaluating custom condition: {e}")
            return False 