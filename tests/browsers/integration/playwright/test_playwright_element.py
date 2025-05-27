import pytest
from pathlib import Path


class TestElementHandleIntegration:
    """Comprehensive integration tests for ElementHandle functionality."""
    
    @pytest.fixture
    async def setup_page(self, playwright_driver):
        """Set up a page with test content for element tests."""
        # Create context and page
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set up test HTML
        test_html = """
        <html>
            <head>
                <title>Element Test Page</title>
                <style>
                    .hidden { display: none; }
                    .disabled { pointer-events: none; opacity: 0.5; }
                </style>
            </head>
            <body>
                <div id="container">
                    <h1 id="main-title">Test Page</h1>
                    <p class="description">This is a test paragraph with <span>nested text</span>.</p>
                    
                    <div id="form-section">
                        <input type="text" id="text-input" value="initial value" />
                        <input type="checkbox" id="checkbox" checked />
                        <select id="dropdown">
                            <option value="opt1">Option 1</option>
                            <option value="opt2" selected>Option 2</option>
                            <option value="opt3">Option 3</option>
                        </select>
                        <textarea id="textarea">Initial text content</textarea>
                        <button id="submit-btn" type="button">Submit</button>
                        <button id="disabled-btn" disabled>Disabled</button>
                    </div>
                    
                    <div id="nested-structure">
                        <div class="parent">
                            <div class="child first">First Child</div>
                            <div class="child second">Second Child</div>
                            <div class="child third">
                                <span class="grandchild">Grandchild Text</span>
                            </div>
                        </div>
                    </div>
                    
                    <div id="visibility-test">
                        <div id="visible-element">Visible</div>
                        <div id="hidden-element" class="hidden">Hidden</div>
                        <div id="display-none" style="display: none;">Display None</div>
                    </div>
                    
                    <ul id="list">
                        <li class="item">Item 1</li>
                        <li class="item">Item 2</li>
                        <li class="item">Item 3</li>
                    </ul>
                    
                    <table id="data-table">
                        <thead>
                            <tr>
                                <th>Column A</th>
                                <th>Column B</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>A1</td>
                                <td>B1</td>
                            </tr>
                            <tr>
                                <td>A2</td>
                                <td>B2</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <div id="attributes-test" 
                         data-custom="custom-value" 
                         class="test-class another-class"
                         title="Test Title">
                        Attributes Test
                    </div>
                </div>
            </body>
        </html>
        """
        
        await playwright_driver.set_page_content(page_id, test_html)
        
        yield playwright_driver, page_id, context_id
        
        # Cleanup
        await playwright_driver.close_page(page_id)
        await playwright_driver.close_context(context_id)
    
    @pytest.mark.asyncio
    async def test_element_text_extraction(self, setup_page):
        """Test various text extraction methods."""
        driver, page_id, _ = setup_page
        
        # Test get_text vs get_inner_text
        p_result = await driver.query_selector(page_id, ".description")
        assert p_result.is_ok()
        p_element = p_result.default_value(None)
        
        # get_text should include all text
        text_result = await p_element.get_text()
        assert text_result.is_ok()
        text = text_result.default_value("")
        print(f"get_text result: '{text}'")
        assert "nested text" in text
        
        # get_inner_text should also include nested text but with proper formatting
        inner_text_result = await p_element.get_inner_text()
        assert inner_text_result.is_ok()
        inner_text = inner_text_result.default_value("")
        print(f"get_inner_text result: '{inner_text}'")
        assert "nested text" in inner_text
        
        # Test on simple element
        h1_result = await driver.query_selector(page_id, "#main-title")
        assert h1_result.is_ok()
        h1_element = h1_result.default_value(None)
        
        h1_text_result = await h1_element.get_text()
        assert h1_text_result.is_ok()
        assert h1_text_result.default_value("") == "Test Page"
    
    @pytest.mark.asyncio
    async def test_element_query_selector_scoping(self, setup_page):
        """Test that query_selector on elements properly scopes to that element."""
        driver, page_id, _ = setup_page
        
        # Get the nested structure container
        container_result = await driver.query_selector(page_id, "#nested-structure")
        assert container_result.is_ok()
        container = container_result.default_value(None)
        
        # Query for child elements within the container
        parent_result = await container.query_selector(".parent")
        assert parent_result.is_ok()
        parent = parent_result.default_value(None)
        assert parent is not None
        
        # Query for children within parent
        children_result = await parent.query_selector_all(".child")
        assert children_result.is_ok()
        children = children_result.default_value([])
        assert len(children) == 3
        
        # Check text of each child
        expected_texts = ["First Child", "Second Child", "Grandchild Text"]
        for i, child in enumerate(children):
            text_result = await child.get_text()
            assert text_result.is_ok()
            text = text_result.default_value("").strip()
            print(f"Child {i} text: '{text}'")
            # The third child contains nested span, so we check if expected text is in it
            if i < 2:
                assert text == expected_texts[i]
            else:
                assert expected_texts[i] in text
    
    @pytest.mark.asyncio
    async def test_table_cell_extraction(self, setup_page):
        """Specific test for table cell extraction to diagnose the original issue."""
        driver, page_id, _ = setup_page
        
        # Get the table
        table_result = await driver.query_selector(page_id, "#data-table")
        assert table_result.is_ok()
        table = table_result.default_value(None)
        
        # Get all rows in tbody
        tbody_rows_result = await table.query_selector_all("tbody tr")
        assert tbody_rows_result.is_ok()
        rows = tbody_rows_result.default_value([])
        assert len(rows) == 2
        
        # Extract cells from first row
        first_row = rows[0]
        cells_result = await first_row.query_selector_all("td")
        assert cells_result.is_ok()
        cells = cells_result.default_value([])
        assert len(cells) == 2
        
        # Get text from each cell
        cell_texts = []
        for cell in cells:
            text_result = await cell.get_text()
            assert text_result.is_ok()
            text = text_result.default_value("").strip()
            cell_texts.append(text)
            print(f"Cell text: '{text}'")
        
        assert cell_texts == ["A1", "B1"]
        
        # Also test with get_inner_text
        inner_texts = []
        for cell in cells:
            inner_text_result = await cell.get_inner_text()
            assert inner_text_result.is_ok()
            inner_text = inner_text_result.default_value("").strip()
            inner_texts.append(inner_text)
            print(f"Cell inner text: '{inner_text}'")
        
        assert inner_texts == ["A1", "B1"]
    
    @pytest.mark.asyncio
    async def test_element_attributes_and_properties(self, setup_page):
        """Test getting attributes and properties from elements."""
        driver, page_id, _ = setup_page
        
        # Get element with attributes
        elem_result = await driver.query_selector(page_id, "#attributes-test")
        assert elem_result.is_ok()
        elem = elem_result.default_value(None)
        
        # Test getting attributes
        custom_attr_result = await elem.get_attribute("data-custom")
        assert custom_attr_result.is_ok()
        assert custom_attr_result.default_value("") == "custom-value"
        
        class_attr_result = await elem.get_attribute("class")
        assert class_attr_result.is_ok()
        assert "test-class" in class_attr_result.default_value("")
        assert "another-class" in class_attr_result.default_value("")
        
        title_attr_result = await elem.get_attribute("title")
        assert title_attr_result.is_ok()
        assert title_attr_result.default_value("") == "Test Title"
        
        # Test non-existent attribute
        nonexistent_result = await elem.get_attribute("nonexistent")
        assert nonexistent_result.is_ok()
        assert nonexistent_result.default_value(None) is None
        
        # Test has_attribute
        assert await elem.has_attribute("data-custom")
        assert not await elem.has_attribute("nonexistent")
    
    @pytest.mark.asyncio
    async def test_element_visibility_and_state(self, setup_page):
        """Test element visibility and enabled state checks."""
        driver, page_id, _ = setup_page
        
        # Test visible element
        visible_result = await driver.query_selector(page_id, "#visible-element")
        assert visible_result.is_ok()
        visible_elem = visible_result.default_value(None)
        
        is_visible_result = await visible_elem.is_visible()
        assert is_visible_result.is_ok()
        assert is_visible_result.default_value(False) is True
        
        # Test hidden element
        hidden_result = await driver.query_selector(page_id, "#hidden-element")
        assert hidden_result.is_ok()
        hidden_elem = hidden_result.default_value(None)
        
        is_hidden_visible_result = await hidden_elem.is_visible()
        assert is_hidden_visible_result.is_ok()
        assert is_hidden_visible_result.default_value(True) is False
        
        # Test enabled/disabled buttons
        enabled_btn_result = await driver.query_selector(page_id, "#submit-btn")
        assert enabled_btn_result.is_ok()
        enabled_btn = enabled_btn_result.default_value(None)
        
        is_enabled_result = await enabled_btn.is_enabled()
        assert is_enabled_result.is_ok()
        assert is_enabled_result.default_value(False) is True
        
        disabled_btn_result = await driver.query_selector(page_id, "#disabled-btn")
        assert disabled_btn_result.is_ok()
        disabled_btn = disabled_btn_result.default_value(None)
        
        is_disabled_enabled_result = await disabled_btn.is_enabled()
        assert is_disabled_enabled_result.is_ok()
        assert is_disabled_enabled_result.default_value(True) is False
    
    @pytest.mark.asyncio
    async def test_element_form_interaction(self, setup_page):
        """Test form element interactions."""
        driver, page_id, _ = setup_page
        
        # Test text input
        input_result = await driver.query_selector(page_id, "#text-input")
        assert input_result.is_ok()
        text_input = input_result.default_value(None)
        
        # Get initial value
        initial_value_result = await text_input.get_property("value")
        assert initial_value_result.is_ok()
        assert initial_value_result.default_value("") == "initial value"
        
        # Fill with new text
        fill_result = await text_input.fill("new text")
        assert fill_result.is_ok()
        
        # Verify new value
        new_value_result = await text_input.get_property("value")
        assert new_value_result.is_ok()
        assert new_value_result.default_value("") == "new text"
        
        # Test select dropdown
        select_result = await driver.query_selector(page_id, "#dropdown")
        assert select_result.is_ok()
        select_elem = select_result.default_value(None)
        
        # Select by value
        select_by_value_result = await select_elem.select(value="opt3")
        assert select_by_value_result.is_ok()
        
        # Verify selection
        selected_value_result = await select_elem.get_property("value")
        assert selected_value_result.is_ok()
        assert selected_value_result.default_value("") == "opt3"
    
    @pytest.mark.asyncio
    async def test_element_parent_children_navigation(self, setup_page):
        """Test navigating between parent and child elements."""
        driver, page_id, _ = setup_page
        
        # Get a child element
        child_result = await driver.query_selector(page_id, ".child.first")
        assert child_result.is_ok()
        child = child_result.default_value(None)
        
        # Get parent
        parent_result = await child.get_parent()
        assert parent_result.is_ok()
        parent = parent_result.default_value(None)
        assert parent is not None
        
        # Verify parent has the right class
        parent_class_result = await parent.get_attribute("class")
        assert parent_class_result.is_ok()
        assert "parent" in parent_class_result.default_value("")
        
        # Get all children of parent
        children_result = await parent.get_children()
        assert children_result.is_ok()
        children = children_result.default_value([])
        assert len(children) == 3
        
        # Verify children texts
        for i, child_elem in enumerate(children):
            text_result = await child_elem.get_text()
            assert text_result.is_ok()
            text = text_result.default_value("").strip()
            print(f"Child {i} text via get_children: '{text}'")
    
    @pytest.mark.asyncio
    async def test_element_html_extraction(self, setup_page):
        """Test getting inner and outer HTML from elements."""
        driver, page_id, _ = setup_page
        
        # Get paragraph with nested span
        p_result = await driver.query_selector(page_id, ".description")
        assert p_result.is_ok()
        p_elem = p_result.default_value(None)
        
        # Get outer HTML
        outer_html_result = await p_elem.get_html(outer=True)
        assert outer_html_result.is_ok()
        outer_html = outer_html_result.default_value("")
        print(f"Outer HTML: {outer_html}")
        assert '<p class="description">' in outer_html
        assert '<span>nested text</span>' in outer_html
        
        # Get inner HTML
        inner_html_result = await p_elem.get_html(outer=False)
        assert inner_html_result.is_ok()
        inner_html = inner_html_result.default_value("")
        print(f"Inner HTML: {inner_html}")
        assert '<span>nested text</span>' in inner_html
        assert '<p class="description">' not in inner_html
    
    @pytest.mark.asyncio
    async def test_element_bounding_box(self, setup_page):
        """Test getting element bounding box."""
        driver, page_id, _ = setup_page
        
        # Get a visible element
        h1_result = await driver.query_selector(page_id, "#main-title")
        assert h1_result.is_ok()
        h1_elem = h1_result.default_value(None)
        
        # Get bounding box
        bbox_result = await h1_elem.get_bounding_box()
        assert bbox_result.is_ok()
        bbox = bbox_result.default_value({})
        
        # Verify bounding box has expected properties
        assert "x" in bbox
        assert "y" in bbox
        assert "width" in bbox
        assert "height" in bbox
        assert bbox["width"] > 0
        assert bbox["height"] > 0
        print(f"Bounding box: {bbox}")
    
    @pytest.mark.asyncio
    async def test_list_item_extraction(self, setup_page):
        """Test extracting items from a list."""
        driver, page_id, _ = setup_page
        
        # Get the list
        list_result = await driver.query_selector(page_id, "#list")
        assert list_result.is_ok()
        list_elem = list_result.default_value(None)
        
        # Get all list items
        items_result = await list_elem.query_selector_all("li")
        assert items_result.is_ok()
        items = items_result.default_value([])
        assert len(items) == 3
        
        # Extract text from each item
        item_texts = []
        for item in items:
            text_result = await item.get_text()
            assert text_result.is_ok()
            text = text_result.default_value("").strip()
            item_texts.append(text)
            print(f"List item text: '{text}'")
        
        assert item_texts == ["Item 1", "Item 2", "Item 3"]