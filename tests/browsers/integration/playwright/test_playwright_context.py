import pytest
import asyncio
from silk.browsers.drivers.playwright import PlaywrightDriver


class TestBrowserContextIntegration:
    """Comprehensive integration tests for BrowserContext functionality."""
    
    @pytest.mark.asyncio
    async def test_context_creation_and_deletion(self, playwright_driver):
        """Test creating and deleting contexts."""
        # Create multiple contexts
        context_ids = []
        for i in range(3):
            context_result = await playwright_driver.create_context()
            assert context_result.is_ok()
            context_id = context_result.default_value(None)
            assert context_id is not None
            context_ids.append(context_id)
        
        # Get all contexts
        contexts_result = await playwright_driver.contexts()
        assert contexts_result.is_ok()
        contexts = contexts_result.default_value([])
        assert len(contexts) >= 3
        
        # Close contexts
        for context_id in context_ids:
            close_result = await playwright_driver.close_context(context_id)
            assert close_result.is_ok()
        
        # Verify contexts are closed
        contexts_result = await playwright_driver.contexts()
        assert contexts_result.is_ok()
        remaining_contexts = contexts_result.default_value([])
        # Should have fewer contexts now
        assert len(remaining_contexts) == len(contexts) - 3
    
    @pytest.mark.asyncio
    async def test_context_with_options(self, playwright_driver):
        """Test creating context with various options."""
        # Create context with viewport size
        options = {
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "TestBot/1.0",
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "color_scheme": "dark"
        }
        
        context_result = await playwright_driver.create_context(options)
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        # Create a page in this context
        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set content to verify options
        html = """
        <html>
            <body>
                <div id="viewport"></div>
                <div id="user-agent"></div>
                <div id="color-scheme"></div>
                <script>
                    document.getElementById('viewport').textContent = 
                        `${window.innerWidth}x${window.innerHeight}`;
                    document.getElementById('user-agent').textContent = 
                        navigator.userAgent;
                    document.getElementById('color-scheme').textContent = 
                        window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                </script>
            </body>
        </html>
        """
        await playwright_driver.set_page_content(page_id, html)
        
        # Verify viewport
        viewport_result = await playwright_driver.execute_script(page_id, 
            "document.getElementById('viewport').textContent")
        assert viewport_result.is_ok()
        assert viewport_result.default_value("") == "1280x720"
        
        # Verify user agent
        ua_result = await playwright_driver.execute_script(page_id, 
            "document.getElementById('user-agent').textContent")
        assert ua_result.is_ok()
        assert "TestBot/1.0" in ua_result.default_value("")
        
        # Verify color scheme
        scheme_result = await playwright_driver.execute_script(page_id, 
            "document.getElementById('color-scheme').textContent")
        assert scheme_result.is_ok()
        assert scheme_result.default_value("") == "dark"
        
        # Cleanup
        await playwright_driver.close_context(context_id)
    
    @pytest.mark.asyncio
    async def test_context_cookies(self, playwright_driver):
        """Test cookie management in contexts."""
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        # Create a page
        page_result = await playwright_driver.create_page(context_id)
        assert page_result.is_ok()
        page_id = page_result.default_value(None)
        
        # Set some content
        await playwright_driver.set_page_content(page_id, """
            <html><body><h1>Cookie Test</h1></body></html>
        """)
        
        # Set cookies
        cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": "localhost",
                "path": "/",
                "expires": -1,  # Session cookie
                "httpOnly": False,
                "secure": False,
                "sameSite": "Lax"
            },
            {
                "name": "another_cookie",
                "value": "another_value",
                "domain": "localhost",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": False,
                "sameSite": "Strict"
            }
        ]
        
        set_result = await playwright_driver.set_context_cookies(context_id, cookies)
        assert set_result.is_ok()
        
        # Get cookies
        get_result = await playwright_driver.get_context_cookies(context_id)
        assert get_result.is_ok()
        retrieved_cookies = get_result.default_value([])
        
        # Verify cookies (may have additional cookies from browser)
        cookie_names = [c["name"] for c in retrieved_cookies]
        assert "test_cookie" in cookie_names
        assert "another_cookie" in cookie_names
        
        # Find our test cookie
        test_cookie = next(c for c in retrieved_cookies if c["name"] == "test_cookie")
        assert test_cookie["value"] == "test_value"
        
        # Clear cookies
        clear_result = await playwright_driver.clear_context_cookies(context_id)
        assert clear_result.is_ok()
        
        # Verify cookies are cleared
        get_after_clear = await playwright_driver.get_context_cookies(context_id)
        assert get_after_clear.is_ok()
        assert len(get_after_clear.default_value([])) == 0
        
        # Cleanup
        await playwright_driver.close_context(context_id)
    
    @pytest.mark.asyncio
    async def test_context_init_script(self, playwright_driver):
        """Test adding initialization scripts to context."""
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        # Add init script that will run on every page
        init_script = """
            window.initScriptRan = true;
            window.customValue = 42;
            window.addEventListener('load', () => {
                window.loadTime = Date.now();
            });
        """
        
        add_result = await playwright_driver.add_context_init_script(context_id, init_script)
        assert add_result.is_ok()
        
        # Create multiple pages and verify script runs on each
        for i in range(3):
            page_result = await playwright_driver.create_page(context_id)
            assert page_result.is_ok()
            page_id = page_result.default_value(None)
            
            # Set content
            await playwright_driver.set_page_content(page_id, f"""
                <html><body><h1>Page {i + 1}</h1></body></html>
            """)
            
            # Verify init script ran
            init_ran_result = await playwright_driver.execute_script(page_id, 
                "window.initScriptRan")
            assert init_ran_result.is_ok()
            assert init_ran_result.default_value(False) is True
            
            custom_value_result = await playwright_driver.execute_script(page_id, 
                "window.customValue")
            assert custom_value_result.is_ok()
            assert custom_value_result.default_value(0) == 42
            
            # Close page
            await playwright_driver.close_page(page_id)
        
        # Cleanup
        await playwright_driver.close_context(context_id)
    

    @pytest.mark.asyncio
    async def test_context_page_management(self, playwright_driver):
        """Test page management within a context."""
        context_result = await playwright_driver.create_context()
        assert context_result.is_ok()
        context_id = context_result.default_value(None)
        
        # Create multiple pages
        page_ids = []
        for i in range(5):
            page_result = await playwright_driver.create_page(context_id)
            assert page_result.is_ok()
            page_id = page_result.default_value(None)
            page_ids.append(page_id)
            
            # Set unique content
            await playwright_driver.set_page_content(page_id, f"""
                <html>
                    <head><title>Page {i + 1}</title></head>
                    <body><h1>Page number {i + 1}</h1></body>
                </html>
            """)
        
        # Get all pages
        pages_result = await playwright_driver.get_context_pages(context_id)
        assert pages_result.is_ok()
        pages = pages_result.default_value([])
        assert len(pages) == 5
        
        # Close some pages
        for page_id in page_ids[:2]:
            await playwright_driver.close_page(page_id)
        
        # Verify page count
        pages_result = await playwright_driver.get_context_pages(context_id)
        assert pages_result.is_ok()
        pages = pages_result.default_value([])
        assert len(pages) == 3
        
        # Close context (should close all remaining pages)
        await playwright_driver.close_context(context_id)
        
        # Verify all pages are closed by trying to access one
        # This should fail since the context is closed
        page_access_result = await playwright_driver.get_page(page_ids[2])
        assert page_access_result.is_error()
    
    @pytest.mark.asyncio
    async def test_context_with_different_viewports(self, playwright_driver):
        """Test contexts with different viewport sizes."""
        viewports = [
            {"width": 375, "height": 667},   # iPhone SE
            {"width": 768, "height": 1024},  # iPad
            {"width": 1920, "height": 1080}, # Desktop
        ]
        
        context_ids = []
        for viewport in viewports:
            context_result = await playwright_driver.create_context({"viewport": viewport})
            assert context_result.is_ok()
            context_id = context_result.default_value(None)
            context_ids.append(context_id)
            
            # Create page and verify viewport
            page_result = await playwright_driver.create_page(context_id)
            assert page_result.is_ok()
            page_id = page_result.default_value(None)
            
            await playwright_driver.set_page_content(page_id, """
                <html><body><div id="size"></div></body></html>
            """)
            
            size_result = await playwright_driver.execute_script(page_id, 
                "({ width: window.innerWidth, height: window.innerHeight })")
            assert size_result.is_ok()
            size = size_result.default_value({})
            assert size["width"] == viewport["width"]
            assert size["height"] == viewport["height"]
        
        # Cleanup
        for context_id in context_ids:
            await playwright_driver.close_context(context_id)
    
    @pytest.mark.asyncio
    async def test_context_mouse_operations(self, playwright_driver: PlaywrightDriver):
        """Test mouse operations through context."""
        context_result = await playwright_driver.new_context()
        assert context_result.is_ok()
        context = context_result.default_value(None)
        
        # Create page through context
        page_result = await context.new_page()
        assert page_result.is_ok()
        page = page_result.default_value(None)
        
        # Set content
        await page.set_content("""
            <html>
                <body>
                    <button id="btn" style="width: 100px; height: 50px;">
                        Click me
                    </button>
                    <div id="log"></div>
                    <script>
                        let clicks = 0;
                        document.getElementById('btn').addEventListener('click', () => {
                            clicks++;
                            document.getElementById('log').textContent = `Clicks: ${clicks}`;
                        });
                    </script>
                </body>
            </html>
        """)
        
        # Use context mouse operations
        # Note: These operations will work on the active page in the context
        move_result = await context.mouse_move(50, 25)
        assert move_result.is_ok()
        
        click_result = await context.mouse_down()
        assert click_result.is_ok()
        click_result = await context.mouse_up()
        assert click_result.is_ok()
        
        # Verify click worked
        log_elem_result = await page.query_selector("#log")
        assert log_elem_result.is_ok()
        log_elem = log_elem_result.default_value(None)
        
        text_result = await log_elem.get_text()
        assert text_result.is_ok()
        assert text_result.default_value("") == "Clicks: 1"
        
        # Cleanup
        await context.close()