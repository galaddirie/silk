# pyright: strict
"""Immutable selector configuration values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator, TypeAlias


class SelectorType(str, Enum):
    """A selector engine or CSS-derived selector form."""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ID = "id"
    CLASS = "class"
    NAME = "name"
    TAG = "tag"
    LINK_TEXT = "link_text"
    SELF = "self"


@dataclass(frozen=True, slots=True)
class Selector:
    """One immutable selector before it is compiled for a browser adapter."""

    type: SelectorType
    value: str

    def is_xpath(self) -> bool:
        return self.type == SelectorType.XPATH

    def is_css(self) -> bool:
        return self.type == SelectorType.CSS

    def __str__(self) -> str:
        return f"{self.type.value}-{self.value}"

    def __repr__(self) -> str:
        return f"Selector(type={self.type}, value={self.value})"


SelectorSpec: TypeAlias = Selector | str | tuple[str, SelectorType | str]


def _normalize_selector(selector: SelectorSpec) -> Selector:
    if isinstance(selector, Selector):
        return selector
    if isinstance(selector, str):
        return Selector(type=SelectorType.CSS, value=selector)
    selector_value, selector_type = selector
    return Selector(type=SelectorType(selector_type), value=selector_value)


@dataclass(frozen=True, slots=True, init=False)
class SelectorGroup:
    """An immutable, ordered set of fallback selectors."""

    name: str
    selectors: tuple[Selector, ...]

    def __init__(self, name: str, *selectors: SelectorSpec) -> None:
        normalized = tuple(_normalize_selector(selector) for selector in selectors)
        if any(selector.type is SelectorType.SELF for selector in normalized):
            raise ValueError("SELF cannot be a fallback inside a SelectorGroup")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "selectors", normalized)

    def __iter__(self) -> Iterator[Selector]:
        return iter(self.selectors)

    def __len__(self) -> int:
        return len(self.selectors)

    def __getitem__(self, index: int) -> Selector:
        return self.selectors[index]

    def __contains__(self, item: Selector) -> bool:
        return item in self.selectors

    def __repr__(self) -> str:
        return f"SelectorGroup(name={self.name}, selectors={self.selectors})"

    def __str__(self) -> str:
        return f"SelectorGroup(name={self.name}, selectors={self.selectors})"


SELF = Selector(type=SelectorType.SELF, value=":self")
"""The scope element itself: ``GetAttribute(SELF, _, attribute="id")`` reads the
focused element's own attribute. Requires an element scope."""


def css(value: str) -> Selector:
    """Create a CSS selector."""

    return Selector(type=SelectorType.CSS, value=value)


def xpath(value: str) -> Selector:
    """Create an XPath selector."""

    return Selector(type=SelectorType.XPATH, value=value)


def text(value: str) -> Selector:
    """Create a text selector."""

    return Selector(type=SelectorType.TEXT, value=value)


__all__ = [
    "SELF",
    "Selector",
    "SelectorGroup",
    "SelectorSpec",
    "SelectorType",
    "css",
    "text",
    "xpath",
]
