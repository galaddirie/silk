# pyright: strict
"""Immutable selector configuration."""

from .selector import (
    Selector,
    SelectorGroup,
    SelectorSpec,
    SelectorType,
    css,
    text,
    xpath,
)

__all__ = [
    "Selector",
    "SelectorGroup",
    "SelectorSpec",
    "SelectorType",
    "css",
    "text",
    "xpath",
]
