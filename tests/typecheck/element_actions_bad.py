# pyright: strict
"""Calls that strict type checkers must reject for element templates."""

from __future__ import annotations

from typing import Self

from fp_ops import Ok, Result, _

from silk.actions.elements import (
    Element,
    ElementScope,
    ElementTarget,
    SelectorInput,
    WaitOptions,
    GetAttribute as get_attribute,
    GetInnerText as get_inner_text,
    Query as query,
    WaitForElement as wait_for_element,
)
from silk.browsers.models import Page
from silk.selectors.selector import SelectorGroup


class ScopeWithoutIdentityHooks:
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


class CloningScope:
    """Structural lookalike whose configured snapshot would change identity."""

    def __copy__(self) -> Self:
        return type(self)()

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        clone = type(self)()
        memo[id(self)] = clone
        return clone

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


class FocusThatOverridesSnapshotPolicy(Page):
    # typecheck-case: element_actions.001
    def __copy__(self) -> Self:
        return self

    # typecheck-case: element_actions.002
    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        return self


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
    # typecheck-case: element_actions.011
    wait_for_element(SelectorGroup("fallback", ".a", ".b"), _)


def missing_identity_hooks_are_rejected(scope: ScopeWithoutIdentityHooks) -> None:
    # typecheck-case: element_actions.012
    query(_, scope)
    # typecheck-case: element_actions.013
    wait_for_element(_, scope)


def cloning_structural_scopes_are_rejected(scope: CloningScope) -> None:
    # typecheck-case: element_actions.014
    query(_, scope)
    # typecheck-case: element_actions.015
    wait_for_element(_, scope)
