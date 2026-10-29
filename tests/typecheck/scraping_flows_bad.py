# pyright: strict
"""Calls that strict type checkers must reject for 0.5 scraping features."""

from fp_ops import Operation, _, derive

from silk.actions.elements import GetText, GetUrl, OwnerPage, optional
from silk.actions.navigation import Navigate
from silk.browsers.models import Page
from silk.scraping import await_change, in_new_page


def misuse(
    page: Page,
    number: Operation[Page, int],
    text: Operation[str, str],
    texts: Operation[Page, list[str]],
) -> None:
    # typecheck-case: scraping_flows.001
    GetUrl(".next", _, attribute=1)
    # typecheck-case: scraping_flows.002
    Navigate(_, derive(number))
    # typecheck-case: scraping_flows.003
    in_new_page(text)
    # typecheck-case: scraping_flows.004
    await_change(GetText("#count", _), probe=texts)
    # typecheck-case: scraping_flows.005
    OwnerPage(page)
    # typecheck-case: scraping_flows.006
    optional(page)
