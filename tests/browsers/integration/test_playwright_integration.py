"""
Tests for the Playwright implementation of the browser driver in Silk.
"""

import pytest

from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.types import BrowserOptions


@pytest.mark.integration
class TestPlaywrightDriverIntegration:
    """Integration tests for PlaywrightDriver using real browser instances."""

    @pytest.fixture
    async def playwright_driver(self):
        """Create a real PlaywrightDriver instance."""
        options = BrowserOptions(
            headless=True,
            timeout=10000,
            viewport_width=1280,
            viewport_height=720,
        )
        driver = PlaywrightDriver(options)

        # Launch the browser
        result = await driver.launch()
        if result.is_error():
            pytest.fail(f"Failed to launch browser: {result.error}")

        try:
            yield driver
        finally:
            # Clean up
            await driver.close()

    @pytest.mark.asyncio
    async def test_navigation_workflow(self, playwright_driver):
        """Test a complete navigation workflow."""
        # Create a context
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)

        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)

        url = "https://www.google.com"
        goto_result = await playwright_driver.goto(page_id, url)
        assert (
            goto_result.is_ok()
        ), f"Failed to navigate to {url}: {goto_result.error if goto_result.is_error() else 'Unknown error'}"

        url_result = await playwright_driver.current_url(page_id)
        assert url_result.is_ok()
        assert "google" in url_result.default_value(None).lower()

        # Get page title using JavaScript
        title_result = await playwright_driver.execute_script(page_id, "document.title")
        assert title_result.is_ok()
        assert "Google" in title_result.default_value(None)

        # Take a screenshot
        screenshot_result = await playwright_driver.screenshot(page_id)
        assert screenshot_result.is_ok()

        # Close the page and context
        await playwright_driver.close_page(page_id)
        await playwright_driver.close_context(context_id)

    @pytest.mark.asyncio
    async def test_form_interaction(self, playwright_driver):
        """Test interaction with a form."""
        # Create a context and page
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)

        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)

        # Create a simple HTML form directly in the page instead of relying on external sites
        form_html = """
        <html>
            <body>
                <form id="test-form">
                    <input type="text" id="name" name="name" placeholder="Name">
                    <input type="email" id="email" name="email" placeholder="Email">
                    <select id="country" name="country">
                        <option value="us">United States</option>
                        <option value="ca">Canada</option>
                        <option value="uk">United Kingdom</option>
                    </select>
                    <textarea id="message" name="message" placeholder="Message"></textarea>
                    <button type="submit" id="submit">Submit</button>
                </form>
                <div id="output"></div>
                <script>
                    document.getElementById('test-form').addEventListener('submit', function(e) {
                        e.preventDefault();
                        const nameVal = document.getElementById('name').value;
                        const emailVal = document.getElementById('email').value;
                        const countryVal = document.getElementById('country').value;
                        const messageVal = document.getElementById('message').value;
                        document.getElementById('output').innerHTML =
                            'Form submitted with: ' + nameVal + ', ' + emailVal + ', ' + countryVal + ', ' + messageVal;
                    });
                </script>
            </body>
        </html>
        """

        # Set the page content directly
        await playwright_driver.pages[page_id].set_content(form_html)

        # Fill the form
        await playwright_driver.fill(page_id, "#name", "Test User")
        await playwright_driver.fill(page_id, "#email", "test@example.com")
        await playwright_driver.select(page_id, "#country", value="ca")
        await playwright_driver.fill(page_id, "#message", "Test message")

        # Submit the form
        await playwright_driver.click(page_id, "#submit")

        # Verify the form submission result
        await playwright_driver.wait_for_selector(page_id, "#output:not(:empty)")

        # Check output text
        output_element_result = await playwright_driver.query_selector(
            page_id, "#output"
        )
        assert output_element_result.is_ok()
        output_element = output_element_result.default_value(None)
        assert output_element is not None

        text_result = await output_element.get_text()
        assert text_result.is_ok()
        output_text = text_result.default_value("")

        assert "Form submitted with: Test User" in output_text
        assert "test@example.com" in output_text
        assert "ca" in output_text
        assert "Test message" in output_text

        # Clean up
        await playwright_driver.close_page(page_id)
        await playwright_driver.close_context(context_id)

    @pytest.mark.asyncio
    async def test_mouse_keyboard_actions(self, playwright_driver):
        """Test mouse and keyboard actions."""
        # Create a context and page
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)

        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)

        # Create a simple HTML page with elements to interact with
        mouse_keyboard_html = """
        <html>
            <body>
                <div id="mouse-area" style="width: 200px; height: 200px; background-color: lightblue; position: relative;">
                    <span id="coordinates">No mouse activity</span>
                </div>
                <input id="keyboard-input" type="text" placeholder="Type here">
                <div id="key-events">No keyboard activity</div>
                <script>
                    const area = document.getElementById('mouse-area');
                    const coords = document.getElementById('coordinates');

                    area.addEventListener('mousemove', function(e) {
                        const rect = area.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        coords.textContent = `Mouse at: ${x.toFixed(0)}, ${y.toFixed(0)}`;
                    });

                    area.addEventListener('click', function(e) {
                        const rect = area.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        coords.textContent = `Clicked at: ${x.toFixed(0)}, ${y.toFixed(0)}`;
                    });

                    const input = document.getElementById('keyboard-input');
                    const events = document.getElementById('key-events');

                    input.addEventListener('input', function(e) {
                        events.textContent = `Input: ${e.target.value}`;
                    });

                    input.addEventListener('keydown', function(e) {
                        events.textContent = `Key down: ${e.key}`;
                    });
                </script>
            </body>
        </html>
        """

        # Set the page content directly
        await playwright_driver.pages[page_id].set_content(mouse_keyboard_html)

        # Test mouse move
        mouse_area_result = await playwright_driver.query_selector(
            page_id, "#mouse-area"
        )
        assert mouse_area_result.is_ok()
        mouse_area = mouse_area_result.default_value(None)
        assert mouse_area is not None

        # Get position of the mouse area
        box_result = await mouse_area.get_bounding_box()
        assert box_result.is_ok()
        box = box_result.default_value({})

        # Move mouse to the center of the area
        move_result = await playwright_driver.mouse_move(
            context_id,
            int(box["x"] + box["width"] / 2),
            int(box["y"] + box["height"] / 2),
        )
        assert move_result.is_ok()

        # Verify mouse coordinates changed
        await playwright_driver.wait_for_selector(
            page_id, "#coordinates:not(:contains('No mouse activity'))"
        )

        # Test mouse click
        click_result = await playwright_driver.mouse_click(context_id)
        assert click_result.is_ok()

        # Verify click was registered
        coords_result = await playwright_driver.query_selector(page_id, "#coordinates")
        assert coords_result.is_ok()
        coords_element = coords_result.default_value(None)
        assert coords_element is not None

        text_result = await coords_element.get_text()
        assert text_result.is_ok()
        coords_text = text_result.default_value("")
        assert "Clicked at:" in coords_text

        # Test keyboard input
        await playwright_driver.click(page_id, "#keyboard-input")
        key_result = await playwright_driver.key_press(context_id, "H")
        assert key_result.is_ok()
        key_result = await playwright_driver.key_press(context_id, "e")
        assert key_result.is_ok()
        key_result = await playwright_driver.key_press(context_id, "l")
        assert key_result.is_ok()
        key_result = await playwright_driver.key_press(context_id, "l")
        assert key_result.is_ok()
        key_result = await playwright_driver.key_press(context_id, "o")
        assert key_result.is_ok()

        # Verify keyboard input was registered
        events_result = await playwright_driver.query_selector(page_id, "#key-events")
        assert events_result.is_ok()
        events_element = events_result.default_value(None)
        assert events_element is not None

        text_result = await events_element.get_text()
        assert text_result.is_ok()

        # Clean up
        await playwright_driver.close_page(page_id)
        await playwright_driver.close_context(context_id)

    @pytest.mark.asyncio
    async def test_element_extraction(self, playwright_driver):
        """Test extracting data from elements."""
        # Create a context and page
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)

        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)

        # Create a simple HTML page with a table to extract data from
        table_html = """
        <html>
            <body>
                <h1>Test Table</h1>
                <table id="test-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Age</th>
                            <th>Location</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>John Doe</td>
                            <td>30</td>
                            <td>New York</td>
                        </tr>
                        <tr>
                            <td>Jane Smith</td>
                            <td>25</td>
                            <td>Los Angeles</td>
                        </tr>
                        <tr>
                            <td>Bob Johnson</td>
                            <td>45</td>
                            <td>Chicago</td>
                        </tr>
                    </tbody>
                </table>
                <div class="link-section">
                    <a href="#section1">Section 1</a>
                    <a href="#section2">Section 2</a>
                    <a href="#section3">Section 3</a>
                </div>
            </body>
        </html>
        """

        # Set the page content directly
        await playwright_driver.pages[page_id].set_content(table_html)

        # Extract text from multiple elements
        links_result = await playwright_driver.query_selector_all(
            page_id, ".link-section a"
        )
        assert links_result.is_ok()
        links = links_result.default_value([])
        assert len(links) > 0

        # Extract text from each link
        link_texts = []
        for link in links:
            text_result = await link.get_text()
            assert text_result.is_ok()
            link_text = text_result.default_value("")
            assert link_text
            link_texts.append(link_text)

        assert len(link_texts) == 3
        assert "Section 1" in link_texts
        assert "Section 2" in link_texts
        assert "Section 3" in link_texts

        # Extract table data
        table_result = await playwright_driver.query_selector(page_id, "#test-table")
        assert table_result.is_ok()
        table = table_result.default_value(None)
        assert table is not None

        table_data_result = await playwright_driver.extract_table(page_id, table)
        assert table_data_result.is_ok()
        table_data = table_data_result.default_value([])

        assert len(table_data) == 3
        assert table_data[0]["Name"] == "John Doe"
        assert table_data[1]["Age"] == "25"
        assert table_data[2]["Location"] == "Chicago"

        # Clean up
        await playwright_driver.close_page(page_id)
        await playwright_driver.close_context(context_id)
