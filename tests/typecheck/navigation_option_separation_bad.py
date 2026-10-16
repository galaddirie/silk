# pyright: strict
"""Calls strict checkers must reject across navigation option families."""

from fp_ops import _

from silk.actions.navigation import (
    NavigateOptions,
    NavigationOptions,
    GoBack as go_back,
    GoForward as go_forward,
    Navigate as navigate,
    Reload as reload,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers.models import Page


def cross_family_misuse(page: Page, url: str) -> None:
    # typecheck-case: navigation_option_separation.001
    navigate(_, url, options=NavigationOptions())
    # typecheck-case: navigation_option_separation.002
    navigate(page, _, options=NavigationOptions())
    # typecheck-case: navigation_option_separation.003
    go_back(_, options=NavigateOptions(referer="https://referrer.test"))
    # typecheck-case: navigation_option_separation.004
    go_forward(_, options=NavigateOptions())
    # typecheck-case: navigation_option_separation.005
    reload(_, options=NavigateOptions())
    # typecheck-case: navigation_option_separation.006
    wait_for_navigation(_, options=NavigateOptions())
    # typecheck-case: navigation_option_separation.007
    page.goto(url, NavigationOptions())


# typecheck-case: navigation_option_separation.008
NavigationOptions(referer="https://impossible.test")
# typecheck-case: navigation_option_separation.009
NavigateOptions(referer=123)
navigate_options = NavigateOptions()
navigation_options = NavigationOptions()
# typecheck-case: navigation_option_separation.010
navigate_options.referer = "https://changed.test"
# typecheck-case: navigation_option_separation.011
navigation_options.wait_until = "networkidle"
