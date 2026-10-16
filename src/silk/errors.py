"""Public domain errors raised by Silk operations."""

from typing import TypeAlias

SelectorReference: TypeAlias = str | tuple[str, ...]


def _describe_selector(selector: SelectorReference) -> str:
    if isinstance(selector, str):
        return repr(selector)
    return "(" + ", ".join(repr(value) for value in selector) + ")"


class ElementNotFoundError(LookupError):
    """No element matched a configured selector or selector fallback group."""

    def __init__(self, selector: SelectorReference) -> None:
        self.selector = selector
        super().__init__(selector)

    def __str__(self) -> str:
        return f"element not found for selector {_describe_selector(self.selector)}"


class AttributeNotFoundError(LookupError):
    """A required attribute was absent from the selected element."""

    def __init__(self, selector: SelectorReference, attribute: str) -> None:
        self.selector = selector
        self.attribute = attribute
        super().__init__(selector, attribute)

    def __str__(self) -> str:
        return (
            f"attribute {self.attribute!r} not found on selector "
            f"{_describe_selector(self.selector)}"
        )


class DragElementMismatchError(ValueError):
    """Drag endpoints do not belong to one pointer owner and page."""

    def __init__(
        self,
        owner_mismatch: bool,
        source_page_id: str,
        target_page_id: str,
    ) -> None:
        self.source_page_id = source_page_id
        self.target_page_id = target_page_id
        self.owner_mismatch = owner_mismatch
        self.page_mismatch = source_page_id != target_page_id
        mismatches: list[str] = []
        if self.owner_mismatch:
            mismatches.append("owner")
        if self.page_mismatch:
            mismatches.append("page")
        self.mismatches = tuple(mismatches)
        super().__init__(owner_mismatch, source_page_id, target_page_id)

    def __str__(self) -> str:
        return "drag elements have mismatched " + " and ".join(self.mismatches)


class PageNotFoundError(LookupError):
    """A successfully inspected browser context lacks a requested page."""

    def __init__(self, page_id: str, context_id: str) -> None:
        self.page_id = page_id
        self.context_id = context_id
        super().__init__(page_id, context_id)

    def __str__(self) -> str:
        return (
            f"page {self.page_id!r} not found in browser context "
            f"{self.context_id!r}"
        )


__all__ = [
    "AttributeNotFoundError",
    "DragElementMismatchError",
    "ElementNotFoundError",
    "PageNotFoundError",
    "SelectorReference",
]
