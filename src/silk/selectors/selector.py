# selectors/selector.py
from enum import Enum
from typing import Awaitable, Callable, Generic, List, Optional, Tuple, TypeVar, Union

from expression.core import Error, Result
from pydantic import BaseModel, Field

T = TypeVar("T")
S = TypeVar("S")


class SelectorType(str, Enum):
    """Enumeration of supported selector types"""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ID = "id"
    CLASS = "class"
    NAME = "name"
    TAG = "tag"
    LINK_TEXT = "link_text"


class Selector(BaseModel):
    """Model representing a selector for finding elements"""

    type: SelectorType
    value: str
    timeout: Optional[int] = Field(default=None)

    def get_type(self) -> SelectorType:
        return self.type

    def get_value(self) -> str:
        return self.value

    def is_xpath(self) -> bool:
        return self.type == SelectorType.XPATH

    def is_css(self) -> bool:
        return self.type == SelectorType.CSS

    def get_timeout(self) -> Optional[int]:
        return self.timeout

    def __str__(self) -> str:
        return f"{self.type.value}-{self.value}"

    def __repr__(self) -> str:
        return f"Selector(type={self.type}, value={self.value})"


class SelectorGroup(BaseModel, Generic[T]):
    """
    A group of selectors representing fallbacks for the same element.

    If one selector fails, the next one will be tried.
    """

    name: str
    selectors: List[Selector] = Field(default_factory=list)

    @classmethod
    def create_mixed(
        cls, name: str, *selectors: Union[Selector, str, Tuple[str, str]]
    ) -> "SelectorGroup[T]":
        """
        Create a selector group from mixed selector types.

        Args:
            name: Name of the selector group
            *selectors: Selectors to group. Can be:
                - Selector objects
                - Strings (assumed to be CSS selectors)
                - Tuples of (value, type)

        Returns:
            A new SelectorGroup instance
        """
        processed_selectors = []

        for selector in selectors:
            if isinstance(selector, Selector):
                processed_selectors.append(selector)
            elif isinstance(selector, str):
                processed_selectors.append(
                    Selector(type=SelectorType.CSS, value=selector)
                )
            elif isinstance(selector, tuple) and len(selector) == 2:
                selector_value, selector_type = selector
                if isinstance(selector_type, str):
                    selector_type = SelectorType(selector_type)
                processed_selectors.append(
                    Selector(type=selector_type, value=selector_value)
                )

        return cls(
            name=name,
            selectors=processed_selectors,
        )

    async def execute(
        self, find_element: Callable[[Selector], Awaitable[Result[T, Exception]]]
    ) -> Result[T, Exception]:
        """
        Try selectors in order until one succeeds

        Args:
            find_element: Function that takes a selector and returns a Result with the found element

        Returns:
            Result containing either the found element or an exception
        """
        for selector in self.selectors:
            result = await find_element(selector)
            if result.is_ok():
                return result

        return Error(Exception(f"All selectors in group '{self.name}' failed"))

    @classmethod
    def create(cls, name: str, *selectors: Selector) -> "SelectorGroup[T]":
        """Factory method to create a selector group"""
        return cls(
            name=name,
            selectors=list(selectors),
        )


class css(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.CSS, value=value)


class xpath(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.XPATH, value=value)


class text(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.TEXT, value=value)
