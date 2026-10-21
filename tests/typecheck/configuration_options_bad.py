"""Negative static contracts for strict browser configuration values."""

from silk.actions.elements import WaitOptions
from silk.actions.navigation import NavigationOptions
from silk.browsers.models import BrowserContextOptions, BrowserOptions
from silk.selectors import Selector, SelectorType

# typecheck-case: configuration_options.001
BrowserOptions(browser_type="chromium")
# typecheck-case: configuration_options.002
BrowserOptions(user_agent="Legacy/1.0")
# typecheck-case: configuration_options.003
BrowserOptions(ignore_https_errors=True)
# typecheck-case: configuration_options.004
BrowserOptions(viewport_width=777, viewport_height=555)
# typecheck-case: configuration_options.005
BrowserOptions(headless=1)
# typecheck-case: configuration_options.006
BrowserOptions(timeout="30000")
# typecheck-case: configuration_options.007
BrowserOptions(args=["--disable-gpu"])
# typecheck-case: configuration_options.008
BrowserOptions(proxy="http://proxy.test")

# typecheck-case: configuration_options.009
BrowserContextOptions(viewport={"width": 1280, "height": 720})
# typecheck-case: configuration_options.011
BrowserContextOptions(proxy={"server": "http://proxy.test"})
# typecheck-case: configuration_options.012
BrowserContextOptions(timeout="500")
# typecheck-case: configuration_options.013
BrowserContextOptions(navigation_timeout="1000")
# typecheck-case: configuration_options.014
BrowserContextOptions(ignore_https_errors=1)
# typecheck-case: configuration_options.015
BrowserContextOptions(java_script_enabled=0)
# typecheck-case: configuration_options.016
BrowserContextOptions(disable_javascript=True)

# typecheck-case: configuration_options.017
NavigationOptions(timeout="2000")
# typecheck-case: configuration_options.018
NavigationOptions(wait_until="complete")
# typecheck-case: configuration_options.019
NavigationOptions(extra=True)
# typecheck-case: configuration_options.020
WaitOptions(timeout="250")
# typecheck-case: configuration_options.021
WaitOptions(state="ready")
# typecheck-case: configuration_options.022
WaitOptions(poll_interval=10)
# typecheck-case: configuration_options.023
Selector(SelectorType.CSS, ".item", timeout=250)

launch = BrowserOptions()
context = BrowserContextOptions()
navigation = NavigationOptions()
wait = WaitOptions()
# typecheck-case: configuration_options.024
launch.timeout = 1
# typecheck-case: configuration_options.025
context.timeout = 1
# typecheck-case: configuration_options.026
navigation.wait_until = "load"
# typecheck-case: configuration_options.027
wait.state = "hidden"
