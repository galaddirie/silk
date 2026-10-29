# pyright: strict
"""Calls that strict type checkers must reject for element templates."""

from __future__ import annotations

from fp_ops import Ok, Result, _

from silk.actions.elements import (
    Element,
    ElementScope,
    ElementTarget,
    GetAttribute as get_attribute,
    GetInnerText as get_inner_text,
    Query as query,
    SelectorInput,
    WaitForElement as wait_for_element,
    WaitOptions,
)


class StructuralLookalikeScope:
    async def query_selector(
        self,
        selector: str,
    ) -> Result[Element | None, Exception]:
        return Ok(None)

    async def query_selector_all(
        self,
        selector: str,
    ) -> Result[list[Element], Exception]:
        return Ok([])

    async def wait_for_selector(
        self,
        selector: str,
        options: WaitOptions | None = None,
    ) -> Result[Element | None, Exception]:
        return Ok(None)


def invalid_template_calls(
    selector: SelectorInput,
    target: ElementTarget,
    scope: ElementScope,
) -> None:
    # typecheck-case: element_actions.003
    query(selector, scope)
    # typecheck-case: element_actions.004
    query(_, _)
    # typecheck-case: element_actions.005
    query(1, _)
    # typecheck-case: element_actions.006
    get_inner_text(1, _)
    # typecheck-case: element_actions.007
    get_inner_text(target, 1)
    # typecheck-case: element_actions.008
    get_attribute(target, _, attribute=1)
    # typecheck-case: element_actions.009
    wait_for_element(".ready", scope)
    # typecheck-case: element_actions.010
    wait_for_element(_, _)


def structural_lookalike_scopes_are_rejected(scope: StructuralLookalikeScope) -> None:
    # typecheck-case: element_actions.012
    query(_, scope)
    # typecheck-case: element_actions.013
    wait_for_element(_, scope)
