# pyright: strict
"""Raw adapter ownership and native handles are not part of the public interfaces.

Drivers are injected only through ``BrowserSession(driver=...)``; pipelines see
a ``Browser`` that cannot close the session's browser.
"""

from silk.browsers.drivers import PlaywrightDriver
from silk.browsers.drivers.playwright import (
    PlaywrightBrowser,
    PlaywrightBrowserContext,
    PlaywrightElementHandle,
    PlaywrightPage,
)
from silk.browsers.models import Browser, BrowserContext, ElementHandle, Page
from silk.browsers.sessions import BrowserSession


def nominal_focus_escapes(
    context: BrowserContext,
    page: Page,
    element: ElementHandle,
) -> None:
    # typecheck-case: browser_seam_escape.001
    context.driver.close()
    # typecheck-case: browser_seam_escape.002
    context.context_ref.close()
    # typecheck-case: browser_seam_escape.003
    page.driver.close()
    # typecheck-case: browser_seam_escape.004
    page.page_ref.close()
    # typecheck-case: browser_seam_escape.005
    page.as_native()
    # typecheck-case: browser_seam_escape.006
    element.driver.close()
    # typecheck-case: browser_seam_escape.007
    element.element_ref.click()
    # typecheck-case: browser_seam_escape.008
    element.as_native()
    # typecheck-case: browser_seam_escape.009
    element.element_id
    # typecheck-case: browser_seam_escape.010
    element._pointer_owner_identity
    # typecheck-case: browser_seam_escape.011
    element._bounding_box
    # typecheck-case: browser_seam_escape.012
    element._move_pointer
    # typecheck-case: browser_seam_escape.013
    element._drag_pointer


def concrete_focus_escapes(
    context: PlaywrightBrowserContext,
    page: PlaywrightPage,
    element: PlaywrightElementHandle,
) -> None:
    # typecheck-case: browser_seam_escape.014
    context.driver.close()
    # typecheck-case: browser_seam_escape.015
    context.context_ref.close()
    # typecheck-case: browser_seam_escape.016
    page.driver.close()
    # typecheck-case: browser_seam_escape.017
    page.page_ref.close()
    # typecheck-case: browser_seam_escape.018
    element.driver.close()
    # typecheck-case: browser_seam_escape.019
    element.element_ref.click()
    # typecheck-case: browser_seam_escape.020
    element.element_id
    # typecheck-case: browser_seam_escape.021
    element._pointer_owner_identity
    # typecheck-case: browser_seam_escape.023
    element._move_pointer
    # typecheck-case: browser_seam_escape.024
    element._drag_pointer


async def environment_browser_cannot_recover_umbrella_close(
    browser: Browser,
) -> None:
    outcome = await browser.new_context()
    # typecheck-case: browser_seam_escape.025
    await outcome.ok.driver.close()
    # typecheck-case: browser_seam_escape.026
    await outcome.ok.context_ref.close()
    # typecheck-case: browser_seam_escape.034
    await browser.close()


def session_driver_injection_is_typed() -> None:
    # typecheck-case: browser_seam_escape.028
    BrowserSession(driver_class=PlaywrightDriver)
    session = BrowserSession()
    # typecheck-case: browser_seam_escape.029
    session.driver
    # typecheck-case: browser_seam_escape.031
    session._driver_factory
    # typecheck-case: browser_seam_escape.032
    BrowserSession(driver_factory=object)
    # typecheck-case: browser_seam_escape.033
    BrowserSession._for_testing(object)
    # typecheck-case: browser_seam_escape.035
    BrowserSession(driver=PlaywrightBrowser)
    # typecheck-case: browser_seam_escape.036
    BrowserSession(driver=PlaywrightDriver(browser_type="chrome"))
