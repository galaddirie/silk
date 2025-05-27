import pytest
import asyncio
from pathlib import Path
import tempfile
from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.models import WaitOptions
from typing import AsyncGenerator

class TestPageIntegration:
    """Comprehensive integration tests for Page functionality."""
    
    SetupContext = tuple[PlaywrightDriver, str]
    
    @pytest.fixture
    async def setup_context(self, playwright_driver: PlaywrightDriver) -> AsyncGenerator[tuple[PlaywrightDriver, str], None]:
        """Set up a context for page tests."""
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        yield playwright_driver, context_id
        
        # Cleanup
        await playwright_driver.close_context(context_id)
    
    @pytest.mark.asyncio
    async def test_page_navigation(self, setup_context: SetupContext):
        """Test page navigation methods."""
        driver, context_id = setup_context
        
        # Create a page
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set initial content
        initial_html = """
        <html>
            <head><title>Page 1</title></head>
            <body>
                <h1>First Page</h1>
                <a href="#" id="link">Go to second page</a>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, initial_html)
        
        # Get initial URL
        url_result = await driver.current_url(page_id)
        assert url_result.is_ok()
        initial_url = url_result.default_value("")
        print(f"Initial URL: {initial_url}")
        
        # Get title
        title_result = await driver.get_page_title(page_id)
        assert title_result.is_ok()
        assert title_result.default_value("") == "Page 1"
        
        # Set new content (simulating navigation)
        second_html = """
        <html>
            <head><title>Page 2</title></head>
            <body>
                <h1>Second Page</h1>
                <a href="#" id="back">Go back</a>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, second_html)
        
        # Verify title changed
        new_title_result = await driver.get_page_title(page_id)
        assert new_title_result.is_ok()
        assert new_title_result.default_value("") == "Page 2"
        
        # Get page content
        content_result = await driver.get_source(page_id)
        assert content_result.is_ok()
        content = content_result.default_value("")
        assert "Second Page" in content
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_wait_for_selector(self, setup_context: SetupContext):
        """Test waiting for selectors to appear."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set initial content without the target element
        initial_html = """
        <html>
            <body>
                <div id="container">
                    <button id="add-btn">Add Element</button>
                </div>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, initial_html)
        
        # Add JavaScript to add element after delay
        script = """
        document.getElementById('add-btn').addEventListener('click', () => {
            setTimeout(() => {
                const newDiv = document.createElement('div');
                newDiv.id = 'delayed-element';
                newDiv.textContent = 'I appeared!';
                document.getElementById('container').appendChild(newDiv);
            }, 100);
        });
        """
        await driver.execute_script(page_id, script)
        
        # Click button to trigger delayed element
        click_result = await driver.click(page_id, "#add-btn")
        assert click_result.is_ok()
        
        # Wait for the element to appear
        wait_result = await driver.wait_for_selector(page_id, "#delayed-element", WaitOptions(timeout=5000, state="visible"))
        assert wait_result.is_ok()
        element = wait_result.default_value(None)
        assert element is not None
        
        # Verify element text
        text_result = await element.get_text()
        assert text_result.is_ok()
        assert text_result.default_value("") == "I appeared!"
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_execute_script(self, setup_context: SetupContext):
        """Test executing JavaScript in the page."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set content
        html = """
        <html>
            <body>
                <div id="counter">0</div>
                <div id="data" data-value="test"></div>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, html)
        
        # Execute script to get data
        result = await driver.execute_script(page_id,
            "() => document.getElementById('data').getAttribute('data-value')")
        assert result.is_ok()
        assert result.default_value("") == "test"
        
        # Execute script to modify DOM
        modify_result = await driver.execute_script(page_id, """
            () => {
                const counter = document.getElementById('counter');
                counter.textContent = '5';
                return counter.textContent;
            }
        """)
        assert modify_result.is_ok()
        assert modify_result.default_value("") == "5"
        
        # Execute script with arguments
        math_result = await driver.execute_script(page_id, 
            "([a, b]) => a + b", [10, 20])
        assert math_result.is_ok()
        assert math_result.default_value(0) == 30
        
        # Execute script that returns complex object
        obj_result = await driver.execute_script(page_id, """
            () => ({
                title: document.title,
                elementCount: document.querySelectorAll('*').length,
                hasCounter: !!document.getElementById('counter')
            })
        """)
        assert obj_result.is_ok()
        obj = obj_result.default_value({})
        assert obj["hasCounter"] is True
        assert obj["elementCount"] > 0
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_screenshot(self, setup_context: SetupContext):
        """Test taking screenshots."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set colorful content for screenshot
        html = """
        <html>
            <head>
                <style>
                    body { margin: 0; padding: 20px; background: #f0f0f0; }
                    .box { 
                        width: 200px; 
                        height: 200px; 
                        background: linear-gradient(45deg, #ff0000, #00ff00); 
                        margin: 20px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    h1 { color: #333; font-family: Arial, sans-serif; }
                </style>
            </head>
            <body>
                <h1>Screenshot Test</h1>
                <div class="box"></div>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, html)
        
        # Take screenshot to bytes
        bytes_result = await driver.screenshot(page_id)
        assert bytes_result.is_ok()
        screenshot_bytes = bytes_result.default_value(b"")
        assert len(screenshot_bytes) > 0
        assert screenshot_bytes[:4] == b'\x89PNG'  # PNG header
        
        # Take screenshot to file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        file_result = await driver.screenshot(page_id, tmp_path)
        assert file_result.is_ok()
        assert tmp_path.exists()
        assert tmp_path.stat().st_size > 0
        
        # Cleanup
        tmp_path.unlink()
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_mouse_operations(self, setup_context: SetupContext):
        """Test mouse operations on the page."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set content with mouse tracking
        html = """
        <html>
            <head>
                <style>
                    #canvas { 
                        width: 400px; 
                        height: 400px; 
                        border: 1px solid black; 
                        position: relative;
                    }
                    .dot {
                        width: 10px;
                        height: 10px;
                        background: red;
                        border-radius: 50%;
                        position: absolute;
                        transform: translate(-50%, -50%);
                    }
                </style>
            </head>
            <body>
                <div id="canvas"></div>
                <div id="click-count">0</div>
                <div id="mouse-pos">x: 0, y: 0</div>
                <script>
                    const canvas = document.getElementById('canvas');
                    const clickCount = document.getElementById('click-count');
                    const mousePos = document.getElementById('mouse-pos');
                    let clicks = 0;
                    
                    canvas.addEventListener('click', (e) => {
                        clicks++;
                        clickCount.textContent = clicks;
                        
                        const dot = document.createElement('div');
                        dot.className = 'dot';
                        dot.style.left = e.offsetX + 'px';
                        dot.style.top = e.offsetY + 'px';
                        canvas.appendChild(dot);
                    });
                    
                    document.addEventListener('mousemove', (e) => {
                        mousePos.textContent = `x: ${e.pageX}, y: ${e.pageY}`;
                        window.mouseX = e.pageX;
                        window.mouseY = e.pageY;
                    });
                </script>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, html)
        
        move_result = await driver.mouse_move(page_id, 100, 100)
        assert move_result.is_ok()
        click_result = await driver.mouse_click(page_id, "left")
        assert click_result.is_ok()
        
        # Verify click was registered
        click_count_result = await driver.execute_script(page_id, 
            "document.getElementById('click-count').textContent")
        assert click_count_result.is_ok()
        assert click_count_result.default_value("0") == "1"
        
        # Test mouse drag
        drag_result = await driver.mouse_drag(page_id, (50, 50), (200, 200))
        assert drag_result.is_ok()
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_keyboard_operations(self, setup_context: SetupContext):
        """Test keyboard operations on the page."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set content with keyboard tracking
        html = """
        <html>
            <body>
                <input type="text" id="input" />
                <div id="key-log"></div>
                <script>
                    const input = document.getElementById('input');
                    const log = document.getElementById('key-log');
                    const keys = [];
                    
                    document.addEventListener('keydown', (e) => {
                        keys.push(`down:${e.key}`);
                        log.textContent = keys.join(', ');
                    });
                    
                    document.addEventListener('keyup', (e) => {
                        keys.push(`up:${e.key}`);
                        log.textContent = keys.join(', ');
                    });
                </script>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, html)
        
        # Focus input
        await driver.click(page_id, "#input")
        
        # Type some text
        type_result = await driver.type(page_id, "#input", "Hello")
        assert type_result.is_ok()
        
        # Verify text was typed
        value_result = await driver.execute_script(page_id, 
            "document.getElementById('input').value")
        assert value_result.is_ok()
        assert value_result.default_value("") == "Hello"
        
        # Test key press
        key_result = await driver.key_press(page_id, "Enter")
        assert key_result.is_ok()
        
        # Test key down/up
        down_result = await driver.key_down(page_id, "Shift")
        assert down_result.is_ok()
        
        up_result = await driver.key_up(page_id, "Shift")
        assert up_result.is_ok()
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_page_scroll(self, setup_context: SetupContext):
        """Test page scrolling."""
        driver, context_id = setup_context
        
        page_result = await driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set tall content
        html = """
        <html>
            <head>
                <style>
                    body { margin: 0; padding: 0; }
                    .section { height: 500px; padding: 20px; }
                    #section1 { background: #ff0000; }
                    #section2 { background: #00ff00; }
                    #section3 { background: #0000ff; }
                </style>
            </head>
            <body>
                <div id="section1" class="section">Section 1</div>
                <div id="section2" class="section">Section 2</div>
                <div id="section3" class="section">Section 3</div>
                <script>
                    window.addEventListener('scroll', () => {
                        window.lastScrollY = window.scrollY;
                    });
                </script>
            </body>
        </html>
        """
        await driver.set_page_content(page_id, html)
        
        # Scroll to specific position
        scroll_result = await driver.scroll(page_id, 0, 500)
        assert scroll_result.is_ok()
        
        # Verify scroll position
        scroll_y_result = await driver.execute_script(page_id, "window.scrollY")
        assert scroll_y_result.is_ok()
        assert scroll_y_result.default_value(0) == 500
        
        # Scroll to element
        scroll_to_elem_result = await driver.scroll(page_id, selector="#section3")
        assert scroll_to_elem_result.is_ok()
        
        await driver.close_page(page_id)
    
    @pytest.mark.asyncio
    async def test_multiple_pages(self, setup_context: SetupContext):
        """Test working with multiple pages."""
        driver, context_id = setup_context
        
        # Create multiple pages
        page_ids = []
        for i in range(3):
            page_result = await driver.create_page(context_id)
            assert page_result.is_ok()
            page_id = page_result.default_value(None)
            page_ids.append(page_id)
            
            # Set unique content for each page
            await driver.set_page_content(page_id, f"""
                <html>
                    <head><title>Page {i + 1}</title></head>
                    <body><h1>This is page {i + 1}</h1></body>
                </html>
            """)
        
        # Get all pages in context
        pages_result = await driver.get_context_pages(context_id)
        assert pages_result.is_ok()
        pages = pages_result.default_value([])
        assert len(pages) == 3
        
        # Verify each page
        for i, page in enumerate(pages):
            title_result = await driver.get_page_title(page.page_id)
            assert title_result.is_ok()
            # Pages might not be in creation order
            assert title_result.default_value("") in ["Page 1", "Page 2", "Page 3"]
        
        # Close one page
        await driver.close_page(page_ids[0])
        
        # Verify page count
        pages_result = await driver.get_context_pages(context_id)
        assert pages_result.is_ok()
        pages = pages_result.default_value([])
        assert len(pages) == 2
        
        # Close remaining pages
        for page_id in page_ids[1:]:
            await driver.close_page(page_id)