# pyright: strict
"""Public behavior for immutable selector configuration."""

from dataclasses import FrozenInstanceError

import pytest

from silk.selectors import (
    Selector,
    SelectorGroup,
    SelectorType,
    css,
    text,
    xpath,
)


def test_selector_is_an_immutable_typed_value() -> None:
    selector = Selector(SelectorType.CSS, ".card")

    assert selector.type is SelectorType.CSS
    assert selector.value == ".card"
    assert not hasattr(selector, "timeout")
    assert selector.is_css()
    assert not selector.is_xpath()

    with pytest.raises(FrozenInstanceError):
        selector.value = ".changed"


def test_selector_constructors_choose_the_declared_engine() -> None:
    assert css(".card") == Selector(SelectorType.CSS, ".card")
    assert xpath("//article") == Selector(SelectorType.XPATH, "//article")
    assert text("Featured") == Selector(SelectorType.TEXT, "Featured")


def test_selector_group_normalizes_inputs_into_an_immutable_tuple() -> None:
    first = css(".preferred")
    group = SelectorGroup(
        "item",
        first,
        ".fallback",
        ("//article", "xpath"),
        ("Read more", SelectorType.TEXT),
    )

    assert group.name == "item"
    assert group.selectors == (
        first,
        Selector(SelectorType.CSS, ".fallback"),
        Selector(SelectorType.XPATH, "//article"),
        Selector(SelectorType.TEXT, "Read more"),
    )
    assert tuple(group) == group.selectors
    assert len(group) == 4
    assert group[0] is first
    assert first in group

    with pytest.raises(FrozenInstanceError):
        group.name = "changed"


def test_selector_group_rejects_unknown_selector_types() -> None:
    with pytest.raises(ValueError):
        SelectorGroup("item", ("value", "unknown"))
