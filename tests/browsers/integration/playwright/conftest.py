import pytest

from silk.browsers.models import BrowserOptions
from silk.browsers.sessions import BrowserSession


@pytest.fixture
async def browser_session():
    """Create a real browser through Silk's public ownership root."""
    options = BrowserOptions(headless=True, timeout=10_000)
    async with BrowserSession(options=options) as session:
        yield session
