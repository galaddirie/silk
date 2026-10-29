# pyright: strict
"""Typed contracts for 0.5 scraping features."""

from __future__ import annotations

from fp_ops import (
    Continue,
    Operation,
    Stop,
    _,
    build,
    continue_if,
    derive,
    loop,
    passthrough,
    retry,
)
from typing_extensions import assert_type

from silk.actions.browser import OpenPage
from silk.actions.elements import (
    ContentFrame,
    Element,
    ElementExists,
    ElementScope,
    GetAttribute,
    GetText,
    GetUrl,
    OwnerPage,
    WaitForElement,
    optional,
)
from silk.actions.input import Click
from silk.actions.navigation import Navigate
from silk.browsers.models import Frame, Page
from silk.errors import BrowserTimeoutError, NavigationError
from silk.scraping import await_change, in_new_page
from silk.selectors import SELF, SelectorGroup, css, xpath

NEXT = SelectorGroup("next", css("a[rel=next]"), xpath("//a[contains(., 'Next')]"))

assert_type(GetUrl(NEXT, _), Operation[ElementScope, str])
assert_type(optional(GetText(".location", _)), Operation[ElementScope, str | None])
assert_type(GetAttribute(SELF, _, attribute="id"), Operation[ElementScope, str | None])
assert_type(OwnerPage(_), Operation[Element, Page])
assert_type(ContentFrame("iframe", _), Operation[ElementScope, Frame])
assert_type(WaitForElement(NEXT, _), Operation[Page | Frame, Element | None])
assert_type(OpenPage(_), Operation[str, Page])


class Card:
    def __init__(self, title: str, url: str, location: str | None) -> None:
        self.title = title
        self.url = url
        self.location = location


card = build(
    Card,
    title=GetText("h2", _),
    url=GetUrl("a", _),
    location=optional(GetText(".loc", _)),
)
assert_type(card, Operation[ElementScope, Card])

# Follow the next link: the URL is read from the page being navigated.
follow_next: Operation[Page, Page] = retry(
    Navigate(_, derive(GetUrl(NEXT, _))),
    attempts=3,
    on=(BrowserTimeoutError, NavigationError),
)
step: Operation[Page, Continue[Page] | Stop[Page]] = continue_if(
    ElementExists(NEXT, _), follow_next
)
assert_type(loop(step, max_steps=50), Operation[Page, Page])

click_next: Operation[Page, Page] = passthrough(Click(NEXT, _))
first_title: Operation[Page, str] = GetText("h2", _)
changed = await_change(click_next, probe=first_title, attempts=2)
assert_type(changed, Operation[Page, Page])

assert_type(in_new_page(GetText("h1", _)), Operation[str, str])
assert_type(in_new_page(GetText("h1", _), isolated=True), Operation[str, str])
