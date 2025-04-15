from enum import Enum
from typing import Awaitable, Callable, List, Optional, Tuple, TypeVar, Union, Iterator

from expression import Error, Result

T = TypeVar("T")


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


class Selector:
    """Model representing a selector for finding elements"""

    def __init__(self, type: SelectorType, value: str, timeout: Optional[int] = None):
        self.type = type
        self.value = value
        self.timeout = timeout

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


class SelectorGroup:
    """
    A group of selectors representing fallbacks for the same element.

    If one selector fails, the next one will be tried.
    """

    def __init__(self, name: str, *selectors: Union[Selector, str, Tuple[str, str]]):
        """
        Initialize a selector group with a name and selectors.

        Args:
            name: Name of the selector group
            *selectors: Selectors to include in the group. Can be:
                - Selector objects
                - Strings (assumed to be CSS selectors)
                - Tuples of (value, type)
        """
        self.name = name
        self.selectors: List[Selector] = []

        for selector in selectors:
            if isinstance(selector, Selector):
                self.selectors.append(selector)
            elif isinstance(selector, str):
                self.selectors.append(Selector(type=SelectorType.CSS, value=selector))
            elif isinstance(selector, tuple) and len(selector) == 2:
                selector_value, selector_type = selector
                if isinstance(selector_type, str):
                    selector_type = SelectorType(selector_type)
                self.selectors.append(
                    Selector(type=selector_type, value=selector_value)
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
    
    


class css(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.CSS, value=value)


class xpath(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.XPATH, value=value)


class text(Selector):
    def __init__(self, value: str):
        super().__init__(type=SelectorType.TEXT, value=value)
