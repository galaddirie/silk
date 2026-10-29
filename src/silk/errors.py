"""Public domain errors raised by Silk operations."""

from typing import TypeAlias

SelectorReference: TypeAlias = str | tuple[str, ...]


def _describe_selector(selector: SelectorReference) -> str:
    if isinstance(selector, str):
        return repr(selector)
    return "(" + ", ".join(repr(value) for value in selector) + ")"


class NotFoundError(LookupError):
    """A lookup succeeded and found nothing.

    Raised only after the browser answered, so ``optional`` can turn exactly
    these into ``None`` while real browser failures stay errors.
    """


class ElementNotFoundError(NotFoundError):
    """No element matched a configured selector or selector fallback group."""

    def __init__(self, selector: SelectorReference) -> None:
        self.selector = selector
        super().__init__(selector)

    def __str__(self) -> str:
        return f"element not found for selector {_describe_selector(self.selector)}"


class AttributeNotFoundError(NotFoundError):
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


class BrowserError(Exception):
    """A failure reported by the browser backend; the native error is ``__cause__``."""


class BrowserTimeoutError(BrowserError, TimeoutError):
    """A browser operation timed out."""


class NavigationError(BrowserError):
    """Navigation failed for a reason other than a timeout."""

    def __init__(self, message: str, url: str | None = None) -> None:
        self.message = message
        self.url = url
        super().__init__(message, url)

    def __str__(self) -> str:
        return self.message


class TargetClosedError(BrowserError):
    """The page, context, or browser was closed while being used."""


class UnsupportedOperationError(BrowserError):
    """The backend cannot perform this operation (e.g. clicking a static page)."""


class ChangeTimeoutError(BrowserTimeoutError):
    """An action did not change what ``await_change`` was watching in time."""


class DragElementMismatchError(ValueError):
    """Drag source and target are not on the same page."""

    def __init__(self, source_page_id: str, target_page_id: str) -> None:
        self.source_page_id = source_page_id
        self.target_page_id = target_page_id
        super().__init__(source_page_id, target_page_id)

    def __str__(self) -> str:
        return (
            f"cannot drag from page {self.source_page_id!r} "
            f"to an element on page {self.target_page_id!r}"
        )


class PageNotFoundError(NotFoundError):
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
    "BrowserError",
    "BrowserTimeoutError",
    "ChangeTimeoutError",
    "DragElementMismatchError",
    "ElementNotFoundError",
    "NavigationError",
    "NotFoundError",
    "PageNotFoundError",
    "SelectorReference",
    "TargetClosedError",
    "UnsupportedOperationError",
]
