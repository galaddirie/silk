import pytest
from silk.browsers.models import BrowserOptions

def test_browser_options_defaults():
    options = BrowserOptions()
    assert options.browser_type == "chromium"
    assert options.headless is True
    assert options.timeout == 30000
    assert options.viewport_width == 1366
    assert options.viewport_height == 768
    assert options.navigation_timeout == options.timeout
    assert options.wait_timeout == options.timeout
    assert options.stealth_mode is False
    assert options.proxy is None
    assert options.user_agent is None
    assert options.extra_http_headers == {}
    assert options.ignore_https_errors is False
    assert options.disable_javascript is False
    assert options.browser_args == []
    assert options.extra_args == {}
    assert options.locale is None
    assert options.timezone is None
    assert options.remote_url is None

def test_browser_options_override_timeouts():
    options = BrowserOptions(timeout=60000)
    assert options.timeout == 60000
    assert options.navigation_timeout == 60000
    assert options.wait_timeout == 60000

    options_nav_explicit = BrowserOptions(timeout=60000, navigation_timeout=50000)
    assert options_nav_explicit.timeout == 60000
    assert options_nav_explicit.navigation_timeout == 50000
    assert options_nav_explicit.wait_timeout == 60000

    options_wait_explicit = BrowserOptions(timeout=60000, wait_timeout=40000)
    assert options_wait_explicit.timeout == 60000
    assert options_wait_explicit.navigation_timeout == 60000
    assert options_wait_explicit.wait_timeout == 40000

    options_all_explicit = BrowserOptions(timeout=60000, navigation_timeout=50000, wait_timeout=40000)
    assert options_all_explicit.timeout == 60000
    assert options_all_explicit.navigation_timeout == 50000
    assert options_all_explicit.wait_timeout == 40000
