# pyright: strict
"""Calls that strict type checkers must reject for lifecycle templates."""

from fp_ops import Environment, _

from silk.actions.browser import (
    CloseContext as close_context,
    ClosePage as close_page,
    CreateContext as create_context,
    NewPage as new_page,
    PageById as page_by_id,
    Pages as pages,
)
from silk.browsers.capabilities import (
    DRIVER,
    BrowserDriverCapability,
    BrowserSessionInfo,
)
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserHttpHeaders,
    BrowserProxy,
    BrowserViewport,
    Page,
)


# typecheck-case: browser_actions.001
class SubclassedBrowserViewport(BrowserViewport):
    pass


# typecheck-case: browser_actions.002
class SubclassedBrowserProxy(BrowserProxy):
    pass


# typecheck-case: browser_actions.003
class SubclassedBrowserHttpHeaders(BrowserHttpHeaders):
    pass


def zero_and_two_hole_calls(
    options: BrowserContextOptions,
    context: BrowserContext,
    page: Page,
) -> None:
    # typecheck-case: browser_actions.004
    create_context(options)
    # typecheck-case: browser_actions.005
    new_page(context)
    # typecheck-case: browser_actions.006
    pages(context)
    # typecheck-case: browser_actions.007
    page_by_id("page", context)
    # typecheck-case: browser_actions.008
    close_page(page)
    # typecheck-case: browser_actions.009
    close_context(context)

    # typecheck-case: browser_actions.010
    new_page(_, _)
    # typecheck-case: browser_actions.011
    page_by_id(_, _)


async def wrong_pipeline_inputs(
    context: BrowserContext,
    page: Page,
) -> None:
    # typecheck-case: browser_actions.012
    await create_context(_).run("not options")
    # typecheck-case: browser_actions.013
    await new_page(_).run(page)
    # typecheck-case: browser_actions.014
    await pages(_).run(page)
    # typecheck-case: browser_actions.015
    await page_by_id(_, context).run(7)
    # typecheck-case: browser_actions.016
    await page_by_id("page", _).run(page)
    # typecheck-case: browser_actions.017
    await close_page(_).run(context)
    # typecheck-case: browser_actions.018
    await close_context(_).run(page)


def wrong_environment_capability() -> None:
    # typecheck-case: browser_actions.019
    Environment().with_value(
        DRIVER,
        BrowserSessionInfo(session_id="wrong capability"),
    )


def incompatible_focus_composition() -> None:
    # typecheck-case: browser_actions.020
    create_context(_).then(close_page(_))
    # typecheck-case: browser_actions.021
    new_page(_).then(close_context(_))


def invalid_context_options() -> None:
    # typecheck-case: browser_actions.022
    BrowserContextOptions(headless=True)
    # typecheck-case: browser_actions.023
    BrowserContextOptions(slow_mo=50)
    # typecheck-case: browser_actions.024
    BrowserContextOptions(user_data_dir="/tmp/profile")
    # typecheck-case: browser_actions.025
    BrowserContextOptions(args=["--disable-gpu"])
    # typecheck-case: browser_actions.026
    BrowserContextOptions(ignore_default_args=True)
    # typecheck-case: browser_actions.027
    BrowserContextOptions(viewport={"width": "wide", "height": 720})
    # typecheck-case: browser_actions.028
    BrowserContextOptions(viewport={"width": 1280, "height": 720})
    # typecheck-case: browser_actions.029
    BrowserViewport(width="wide", height=720)
    # typecheck-case: browser_actions.030
    BrowserContextOptions(permissions=(1,))
    # typecheck-case: browser_actions.031
    BrowserContextOptions(extra_http_headers={"x-value": 1})
    # typecheck-case: browser_actions.032
    BrowserContextOptions(extra_http_headers={"x-value": "valid"})
    # typecheck-case: browser_actions.033
    BrowserHttpHeaders({"x-value": 1})
    # typecheck-case: browser_actions.034
    BrowserContextOptions(proxy={"server": "http://proxy.test"})
    # typecheck-case: browser_actions.035
    BrowserProxy(server=123)
    # typecheck-case: browser_actions.036
    BrowserContextOptions(timeout="fast")


def immutable_context_options_cannot_be_mutated() -> None:
    viewport = BrowserViewport(width=1280, height=720)
    headers = BrowserHttpHeaders({"x-value": "original"})
    proxy = BrowserProxy(server="http://proxy.test")
    options = BrowserContextOptions(
        viewport=viewport,
        permissions=("geolocation",),
        extra_http_headers=headers,
        proxy=proxy,
    )

    # typecheck-case: browser_actions.037
    options.timeout = 100
    # typecheck-case: browser_actions.038
    viewport.width = 1
    # typecheck-case: browser_actions.039
    options.permissions[0] = "camera"
    # typecheck-case: browser_actions.040
    headers["x-value"] = "changed"
    # typecheck-case: browser_actions.041
    proxy.server = "http://changed.test"


def capability_does_not_expose_adapter_lifecycle(
    capability: BrowserDriverCapability,
) -> None:
    # typecheck-case: browser_actions.042
    capability.driver
    # typecheck-case: browser_actions.043
    capability.close()
