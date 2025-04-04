from typing import Optional, Any, List, Union, Dict, TypeVar, Generic
from expression.core import Result, Ok, Error
from expression import pipe
from expression.collections import Block
from pydantic import BaseModel

from silk.browser.driver import BrowserDriver
from silk.selectors.selector import Selector, SelectorGroup
from silk.actions.base import Action
from silk.actions.utils import _find_element_and_extract
T = TypeVar('T')

class ExtractText(Action[str]):
    """Action to extract text from an element"""
    
    def __init__(self, selector: Union[Selector, SelectorGroup]):
        selector_str = selector.name if isinstance(selector, SelectorGroup) else str(selector)
        super().__init__(
            name=f"extractText({selector_str})",
            description=f"Extract text from element: {selector_str}"
        )
        self.selector = selector
    
    async def execute(self, driver: BrowserDriver) -> Result[str, Exception]:
        try:
            if isinstance(self.selector, SelectorGroup):
                return await self.selector.execute(
                    lambda sel: _find_element_and_extract(driver, sel, lambda el: el.get_text())
                )
            else:
                return await _find_element_and_extract(
                    driver, self.selector, lambda el: el.get_text()
                )
        except Exception as e:
            return Error(e)


class ExtractAttribute(Action[Optional[str]]):
    """Action to extract an attribute from an element"""
    
    def __init__(self, selector: Union[Selector, SelectorGroup], attribute: str):
        selector_str = selector.name if isinstance(selector, SelectorGroup) else str(selector)
        super().__init__(
            name=f"extractAttribute({selector_str}, {attribute})",
            description=f"Extract attribute '{attribute}' from element: {selector_str}"
        )
        self.selector = selector
        self.attribute = attribute
    
    async def execute(self, driver: BrowserDriver) -> Result[Optional[str], Exception]:
        try:
            if isinstance(self.selector, SelectorGroup):
                return await self.selector.execute(
                    lambda sel: _find_element_and_extract(
                        driver, sel, lambda el: el.get_attribute(self.attribute)
                    )
                )
            else:
                return await _find_element_and_extract(
                    driver, self.selector, lambda el: el.get_attribute(self.attribute)
                )
        except Exception as e:
            return Error(e)


class ExtractMultiple(Action[Block[T]], Generic[T]):
    """Action to extract multiple elements matching a selector"""
    
    def __init__(
        self, 
        selector: Union[Selector, SelectorGroup],
        extract_fn: Any = lambda el: el.get_text()
    ):
        selector_str = selector.name if isinstance(selector, SelectorGroup) else str(selector)
        super().__init__(
            name=f"extractMultiple({selector_str})",
            description=f"Extract multiple elements matching: {selector_str}"
        )
        self.selector = selector
        self.extract_fn = extract_fn
    
    async def execute(self, driver: BrowserDriver) -> Result[Block[T], Exception]:
        try:
            if isinstance(self.selector, Selector):
                # Try CSS first if possible
                css_option = self.selector.to_css()
                
                if css_option.is_some():
                    elements = await driver.query_selector_all(css_option.unwrap())
                    if elements:
                        # Use Block instead of list for immutability
                        results = Block.empty()
                        for el in elements:
                            extracted = await self.extract_fn(el)
                            results = results.cons(extracted)
                        # Reverse because cons adds at the beginning
                        return Ok(pipe(results, Block.reverse))
                
                # Fall back to XPath
                xpath = self.selector.to_xpath()
                elements = await driver.query_selector_all(xpath)
                
                if elements:
                    # Use Block instead of list for immutability
                    results = Block.empty()
                    for el in elements:
                        extracted = await self.extract_fn(el)
                        results = results.cons(extracted)
                    # Reverse because cons adds at the beginning
                    return Ok(pipe(results, Block.reverse))
                else:
                    return Ok(Block.empty())
            else:
                # For SelectorGroup, use the first successful selector
                for selector in self.selector.selectors:
                    result = await self._extract_with_selector(driver, selector)
                    if result.is_ok() and len(result.unwrap()) > 0:
                        return result
                
                # If no selector matched elements, return empty Block
                return Ok(Block.empty())
        except Exception as e:
            return Error(e)
    
    async def _extract_with_selector(
        self, driver: BrowserDriver, selector: Selector
    ) -> Result[Block[T], Exception]:
        try:
            # Try CSS first if possible
            css_option = selector.to_css()
            
            if css_option.is_some():
                elements = await driver.query_selector_all(css_option.unwrap())
                if elements:
                    # Use Block for functional immutability
                    results = pipe(
                        elements,
                        lambda els: Block.of_seq([]),  # Start with empty Block
                        lambda block: self._extract_all_elements(block, elements)
                    )
                    return Ok(results)
            
            # Fall back to XPath
            xpath = selector.to_xpath()
            elements = await driver.query_selector_all(xpath)
            
            if elements:
                # Use Block instead of list for immutability
                results = Block.empty()
                for el in elements:
                    extracted = await self.extract_fn(el)
                    results = results.cons(extracted)
                # Reverse because cons adds at the beginning
                return Ok(pipe(results, Block.reverse))
            else:
                return Ok(Block.empty())
        except Exception as e:
            return Error(e)
            
    async def _extract_all_elements(self, block: Block, elements) -> Block[T]:
        """Helper method to extract from all elements and build a Block"""
        results = Block.empty()
        for el in elements:
            extracted = await self.extract_fn(el)
            results = results.cons(extracted)
        return pipe(results, Block.reverse)


# Helper function for element extraction
