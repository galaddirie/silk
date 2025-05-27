import pytest
from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.models import BrowserOptions


@pytest.fixture
async def playwright_driver():
    """Create a real PlaywrightDriver instance."""
    options = BrowserOptions(
        headless=True,
        timeout=10000,
        viewport_width=1280,
        viewport_height=720,
    )
    driver = PlaywrightDriver()

    # Launch the browser
    result = await driver.launch(options)
    if result.is_error():
        pytest.fail(f"Failed to launch browser: {result.error}")

    try:
        yield driver
    finally:
        # Clean up
        await driver.close()

