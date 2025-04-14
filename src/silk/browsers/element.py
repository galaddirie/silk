import logging
from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from expression import Result

if TYPE_CHECKING:
    from silk.browsers.driver import BrowserDriver
    from silk.browsers.types import TypeOptions

T = TypeVar("T")

logger = logging.getLogger(__name__)


@runtime_checkable
class ElementHandle(Generic[T], Protocol):
    """
    Represents a handle to an element in a web page.

    This class is generic and parameterized by the type of the native element reference
    from the underlying browser automation library (e.g., Playwright ElementHandle,
    Selenium WebElement).

    It provides methods to interact with elements while maintaining type safety
    for the specific automation library being used.
    """

    driver: "BrowserDriver"
    page_id: str
    element_ref: T
    selector: Optional[str]

    def __init__(
        self,
        driver: "BrowserDriver",
        page_id: str,
        element_ref: T,
        selector: Optional[str] = None,
    ):
        """
        Initialize an element handle

        Args:
            driver: The browser driver instance that manages browser interactions
            page_id: ID of the page containing this element for tracking purposes
            element_ref: Reference to the element in the underlying automation library
            selector: The selector used to find this element (optional)
        """
        self.driver = driver
        self.page_id = page_id
        self.element_ref = element_ref
        self.selector = selector

    def get_page_id(self) -> str:
        """
        Get the page ID associated with this element

        Returns:
            The unique identifier of the page containing this element
        """
        return self.page_id

    def get_selector(self) -> Optional[str]:
        """
        Get the selector used to find this element

        Returns:
            The selector string or None if not available
        """
        return self.selector

    @abstractmethod
    async def get_text(self) -> Result[str, Exception]:
        """
        Get the text content of this element

        Returns:
            Result containing the element's text content if successful,
            or an Error with the exception if the operation fails
        """
        pass

    async def text(self) -> str:
        """
        Get the text content of this element (simplified version)

        Returns:
            The element's text content

        Raises:
            Exception: If getting the text fails
        """
        result = await self.get_text()
        if result.is_error():
            raise result.error
        return result.default_value("")

    @abstractmethod
    async def get_inner_text(self) -> Result[str, Exception]:
        """
        Get the innerText of this element (visible text only, excluding hidden elements)

        This differs from get_text() in that it respects CSS styling and only returns
        text that would be visible to the user in the browser.

        Returns:
            Result containing the element's innerText as a string if successful,
            or an Error with the exception if the operation fails
        """
        pass

    @abstractmethod
    async def get_html(self, outer: bool = True) -> Result[str, Exception]:
        """
        Get the HTML content of this element

        Args:
            outer: Whether to include the element's outer HTML (True) or just inner HTML (False).
                  Outer HTML includes the element's own tags, while inner HTML only includes
                  the content between the opening and closing tags.

        Returns:
            Result containing the HTML content as a string if successful,
            or an Error with the exception if the operation fails
        """
        pass

    @abstractmethod
    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        """
        Get an attribute value from this element

        Args:
            name: The name of the attribute to retrieve (e.g., 'id', 'class', 'href')

        Returns:
            Result containing the attribute value (or None if attribute doesn't exist)
            if successful, or an Error with the exception if the operation fails
        """
        pass

    async def attribute(self, name: str, default: str = "") -> str:
        """
        Get an attribute value from this element (simplified version)

        Args:
            name: The name of the attribute to retrieve
            default: Default value to return if attribute doesn't exist

        Returns:
            The attribute value or the default if not found

        Raises:
            Exception: If getting the attribute fails
        """
        result = await self.get_attribute(name)
        if result.is_error():
            raise result.error
        value = result.default_value(default)
        if value is None:
            raise ValueError(f"Attribute {name} is None")
        return value

    async def has_attribute(self, name: str) -> bool:
        """
        Check if this element has the specified attribute

        Args:
            name: The name of the attribute to check

        Returns:
            True if the attribute exists, False otherwise

        Raises:
            Exception: If checking the attribute fails
        """
        result = await self.get_attribute(name)
        if result.is_error():
            raise result.error
        value = result.default_value(None)

        return value is not None

    @abstractmethod
    async def get_property(self, name: str) -> Result[Any, Exception]:
        """
        Get a JavaScript property value from this element

        Args:
            name: The name of the property to retrieve

        Returns:
            Result containing the property value if successful,
            or an Error with the exception if the operation fails
        """
        pass

    @abstractmethod
    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        """
        Get the bounding box of this element

        Returns:
            Result containing a dictionary with the element's position and dimensions
            (typically with 'x', 'y', 'width', 'height' keys) if successful,
            or an Error with the exception if the operation fails
        """
        pass

    @abstractmethod
    async def click(self) -> Result[None, Exception]:
        """
        Click this element

        Simulates a mouse click on the element, triggering any associated event handlers.

        Returns:
            Result indicating success (Ok with None) or an Error with the exception
            if the operation fails
        """
        pass

    @abstractmethod
    async def fill(
        self, text: str, options: Optional["TypeOptions"] = None
    ) -> Result[None, Exception]:
        """
        Fill this element with the given text

        Args:
            text: The text to fill into the element
            options: Optional typing options

        Returns:
            Result indicating success (Ok with None) or an Error with the exception
            if the operation fails
        """
        pass

    async def input(
        self, text: str, options: Optional["TypeOptions"] = None
    ) -> "ElementHandle[T]":
        """
        Fill this element with text and return self for chaining

        Args:
            text: The text to input
            options: Optional typing options

        Returns:
            This element for method chaining

        Raises:
            Exception: If filling fails
        """
        result = await self.fill(text, options)
        if result.is_error():
            raise result.error
        return self

    @abstractmethod
    async def select(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        """
        Select an option from this element

        Args:
            value: The value of the option to select
            text: The text of the option to select

        Returns:
            Result indicating success (Ok with None) or an Error with the exception
            if the operation fails
        """
        pass

    async def choose(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> "ElementHandle[T]":
        """
        Select an option and return self for chaining

        Args:
            value: The value of the option to select
            text: The text of the option to select

        Returns:
            This element for method chaining

        Raises:
            Exception: If selection fails
        """
        result = await self.select(value, text)
        if result.is_error():
            raise result.error
        return self

    @abstractmethod
    async def is_visible(self) -> Result[bool, Exception]:
        """
        Check if this element is visible

        Returns:
            Result containing True if the element is visible, False otherwise,
            or an Error if the check fails
        """
        pass

    @abstractmethod
    async def is_enabled(self) -> Result[bool, Exception]:
        """
        Check if this element is enabled

        Returns:
            Result containing True if the element is enabled, False otherwise,
            or an Error if the check fails
        """
        pass

    @abstractmethod
    async def get_parent(self) -> Result[Optional["ElementHandle"], Exception]:
        """
        Get the parent element

        Returns:
            Result containing the parent element or None if no parent exists,
            or an Error if the operation fails
        """
        pass

    @abstractmethod
    async def get_children(self) -> Result[List["ElementHandle"], Exception]:
        """
        Get all child elements

        Returns:
            Result containing a list of child elements,
            or an Error if the operation fails
        """
        pass

    @abstractmethod
    async def query_selector(
        self, selector: str
    ) -> Result[Optional["ElementHandle"], Exception]:
        """
        Find a descendant element matching the selector

        Args:
            selector: CSS selector to match

        Returns:
            Result containing the matching element or None if not found,
            or an Error if the operation fails
        """
        pass

    @abstractmethod
    async def query_selector_all(
        self, selector: str
    ) -> Result[List["ElementHandle"], Exception]:
        """
        Find all descendant elements matching the selector

        Args:
            selector: CSS selector to match

        Returns:
            Result containing a list of matching elements,
            or an Error if the operation fails
        """
        pass

    @abstractmethod
    async def scroll_into_view(self) -> Result[None, Exception]:
        """
        Scroll this element into view

        Returns:
            Result indicating success (Ok with None) or an Error if the operation fails
        """
        pass

    @asynccontextmanager
    async def with_scroll_into_view(
        self,
    ) -> AsyncGenerator["ElementHandle[T]", None]:
        """
        Context manager that scrolls this element into view

        Example:
            ```
            async with element.with_scroll_into_view() as visible_element:
                await visible_element.click()
            ```

        Yields:
            This element after scrolling it into view

        Raises:
            Exception: If scrolling fails
        """
        result = await self.scroll_into_view()
        if result.is_error():
            raise result.error
        yield self

    def as_native(self) -> T:
        """
        Get the native element reference from the underlying automation library

        This is useful for accessing driver-specific features not abstracted
        by the ElementHandle class.

        Returns:
            The native element reference (type depends on the browser driver)
        """
        return self.element_ref
