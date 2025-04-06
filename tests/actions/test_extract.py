import pytest
from expression import Result, Ok, Error
from expression.collections import Block
from unittest.mock import AsyncMock, MagicMock, patch
from silk.browsers.driver import BrowserDriver, ElementHandle
from silk.selectors.selector import Selector, SelectorGroup
from silk.actions.decorators import unwrap

from silk.actions.extract import (
    ExtractText,
    ExtractAttribute,
)


class TestExtractActions:
    @pytest.mark.asyncio
    async def test_extract_text_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Set up the expected text
        expected_text = "Extracted text content"
        mock_driver.get_text.return_value = expected_text
        
        # Test ExtractText action
        extract_action = ExtractText(mock_selector)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == expected_text
        mock_driver.get_text.assert_called_once_with(mock_selector)

    @pytest.mark.asyncio
    async def test_extract_text_action_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test ExtractText action failure
        mock_driver.get_text.side_effect = Exception("Element not found")
        extract_action = ExtractText(mock_selector)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Element not found" in str(result.error)

    @pytest.mark.asyncio
    async def test_extract_text_with_selector_group(self, mock_driver: AsyncMock, mock_selector_group: MagicMock) -> None:
        # Set up the expected text for the first selector in the group
        expected_text = "Text from first selector"
        mock_driver.get_text.return_value = expected_text
        
        # Test ExtractText action with a selector group
        extract_action = ExtractText(mock_selector_group)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == expected_text
        # Should try with the first selector in the group
        mock_driver.get_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_attribute_action(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Set up the expected attribute value
        attribute_name = "href"
        expected_value = "https://example.com"
        mock_driver.get_attribute.return_value = expected_value
        
        # Test ExtractAttribute action
        extract_action = ExtractAttribute(mock_selector, attribute_name)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value(None) == expected_value
        mock_driver.get_attribute.assert_called_once_with(mock_selector, attribute_name)

    @pytest.mark.asyncio
    async def test_extract_attribute_not_found(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test when attribute is not found (returns None)
        attribute_name = "data-test"
        mock_driver.get_attribute.return_value = None
        
        # ExtractAttribute should still return Ok(None) in this case
        extract_action = ExtractAttribute(mock_selector, attribute_name)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_ok()
        assert result.default_value("default") is None

    @pytest.mark.asyncio
    async def test_extract_attribute_failure(self, mock_driver: AsyncMock, mock_selector: MagicMock) -> None:
        # Test ExtractAttribute action failure
        attribute_name = "class"
        mock_driver.get_attribute.side_effect = Exception("Element not found")
        
        extract_action = ExtractAttribute(mock_selector, attribute_name)
        
        result = await extract_action.execute(mock_driver)
        
        assert result.is_error()
        assert "Element not found" in str(result.error)

    

  