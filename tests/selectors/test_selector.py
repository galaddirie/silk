import pytest
from expression import Result, Ok, Error
from unittest.mock import AsyncMock

from silk.selectors.selector import (
    SelectorType,
    Selector,
    SelectorGroup,
    css,
    xpath,
    text,
)


class TestSelector:
    def test_selector_initialization(self) -> None:
        selector = Selector(type=SelectorType.CSS, value=".test-selector")
        
        assert selector.type == SelectorType.CSS
        assert selector.value == ".test-selector"
        
    def test_selector_methods(self) -> None:
        css_selector = Selector(type=SelectorType.CSS, value=".test-selector")
        xpath_selector = Selector(type=SelectorType.XPATH, value="//div[@class='test']")
        
        assert css_selector.get_type() == SelectorType.CSS
        assert css_selector.get_value() == ".test-selector"
        assert css_selector.is_css() is True
        assert css_selector.is_xpath() is False
        
        assert xpath_selector.get_type() == SelectorType.XPATH
        assert xpath_selector.get_value() == "//div[@class='test']"
        assert xpath_selector.is_css() is False
        assert xpath_selector.is_xpath() is True
        
    def test_selector_string_representation(self) -> None:
        selector = Selector(type=SelectorType.CSS, value=".test-selector")
        
        assert str(selector) == "css:.test-selector"
        # Skipping exact repr test as it's implementation detail and might vary


class TestSelectorGroup:
    def test_selector_group_initialization(self) -> None:
        selector1 = css(".primary-selector")
        selector2 = css(".fallback-selector")
        
        group: SelectorGroup = SelectorGroup.create("test_group", selector1, selector2)
        
        assert group.name == "test_group"
        assert len(group.selectors) == 2
        assert group.selectors[0].value == ".primary-selector"
        assert group.selectors[1].value == ".fallback-selector"
    
    def test_selector_group_create_mixed(self) -> None:
        group: SelectorGroup = SelectorGroup.create_mixed(
            "mixed_group", 
            ".css-selector", 
            css(".another-css"),
            xpath("//div[@id='test']"),
            ("//span[contains(text(),'find me')]", SelectorType.XPATH)
        )
        
        assert group.name == "mixed_group"
        assert len(group.selectors) == 4
        assert group.selectors[0].type == SelectorType.CSS
        assert group.selectors[0].value == ".css-selector"
        assert group.selectors[1].type == SelectorType.CSS
        assert group.selectors[1].value == ".another-css"
        assert group.selectors[2].type == SelectorType.XPATH
        assert group.selectors[2].value == "//div[@id='test']"
        assert group.selectors[3].type == SelectorType.XPATH
        assert group.selectors[3].value == "//span[contains(text(),'find me')]"
    
    @pytest.mark.asyncio
    async def test_selector_group_execute_first_success(self) -> None:
        # Set up selectors
        selector1 = css(".primary-selector")
        selector2 = css(".fallback-selector")
        group: SelectorGroup = SelectorGroup.create("test_group", selector1, selector2)
        
        # Mock find_element function
        mock_find = AsyncMock()
        mock_find.side_effect = [
            Ok("Element found with primary selector")
        ]
        
        # Test execution
        result = await group.execute(mock_find)
        
        assert result.is_ok()
        assert result.default_value(None) == "Element found with primary selector"
        mock_find.assert_called_once_with(selector1)
    
    @pytest.mark.asyncio
    async def test_selector_group_execute_fallback(self) -> None:
        # Set up selectors
        selector1 = css(".primary-selector")
        selector2 = css(".fallback-selector")
        group: SelectorGroup = SelectorGroup.create("test_group", selector1, selector2)
        
        # Mock find_element function
        mock_find = AsyncMock()
        mock_find.side_effect = [
            Error(Exception("Primary selector failed")),
            Ok("Element found with fallback selector")
        ]
        
        # Test execution
        result = await group.execute(mock_find)
        
        assert result.is_ok()
        assert result.default_value(None) == "Element found with fallback selector"
        assert mock_find.call_count == 2
        mock_find.assert_any_call(selector1)
        mock_find.assert_any_call(selector2)
    
    @pytest.mark.asyncio
    async def test_selector_group_execute_all_fail(self) -> None:
        # Set up selectors
        selector1 = css(".primary-selector")
        selector2 = css(".fallback-selector")
        group: SelectorGroup = SelectorGroup.create("test_group", selector1, selector2)
        
        # Mock find_element function
        mock_find = AsyncMock()
        mock_find.side_effect = [
            Error(Exception("Primary selector failed")),
            Error(Exception("Fallback selector failed"))
        ]
        
        # Test execution
        result = await group.execute(mock_find)
        
        assert result.is_error()
        assert "All selectors in group 'test_group' failed" in str(result.error)
        assert mock_find.call_count == 2
        

class TestHelperClasses:
    def test_css_helper(self) -> None:
        selector = css(".test-class")
        
        assert selector.type == SelectorType.CSS
        assert selector.value == ".test-class"
        assert selector.is_css() is True
    
    def test_xpath_helper(self) -> None:
        selector = xpath("//div[@id='test']")
        
        assert selector.type == SelectorType.XPATH
        assert selector.value == "//div[@id='test']"
        assert selector.is_xpath() is True
    
    def test_text_helper(self) -> None:
        selector = text("Find this text")
        
        assert selector.type == SelectorType.TEXT
        assert selector.value == "Find this text" 