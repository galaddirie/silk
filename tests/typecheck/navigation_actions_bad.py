# pyright: strict
"""Negative typing contracts for navigation template arities and inputs."""

from pathlib import Path

from fp_ops import _

from silk.actions.navigation import (
    CurrentUrl as current_url,
    Evaluate as evaluate,
    EvaluateWith as evaluate_with,
    GoBack as go_back,
    Navigate as navigate,
    ScreenshotTo as screenshot_to,
    Title as title,
)
from silk.browsers.models import Page


def zero_hole_calls(page: Page, path: Path) -> None:
    # typecheck-case: navigation_actions.001
    go_back(page)
    # typecheck-case: navigation_actions.002
    title(page)
    # typecheck-case: navigation_actions.003
    navigate(page, "https://example.test")
    # typecheck-case: navigation_actions.004
    screenshot_to(page, path)
    # typecheck-case: navigation_actions.005
    evaluate(page, "return true")
    # typecheck-case: navigation_actions.006
    evaluate_with(page, "value => value", None)


def two_hole_calls(page: Page) -> None:
    # typecheck-case: navigation_actions.007
    go_back(_, _)
    # typecheck-case: navigation_actions.008
    title(_, _)
    # typecheck-case: navigation_actions.009
    navigate(_, _)
    # typecheck-case: navigation_actions.010
    screenshot_to(_, _)
    # typecheck-case: navigation_actions.011
    evaluate(_, _)
    # typecheck-case: navigation_actions.012
    evaluate_with(_, _, None)


async def wrong_operation_inputs(page: Page) -> None:
    # typecheck-case: navigation_actions.013
    await current_url(_).run("not a page")
    # typecheck-case: navigation_actions.014
    await title(_).run("not a page")
    # typecheck-case: navigation_actions.015
    await navigate(_, "https://example.test").run("not a page")
    # typecheck-case: navigation_actions.016
    await navigate(page, _).run(42)
    # typecheck-case: navigation_actions.017
    await screenshot_to(page, _).run("not a path")
    # typecheck-case: navigation_actions.018
    await evaluate(page, _).run(42)
    # typecheck-case: navigation_actions.019
    await evaluate_with(_, "value => value", None).run("not a page")
    # typecheck-case: navigation_actions.020
    await evaluate_with(page, _, None).run(42)
