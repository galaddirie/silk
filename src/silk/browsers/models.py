from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Set,
    Literal,
    Optional,
    Union,
    ParamSpec,
    Tuple,
    Generic,
    TypeVar,
    Protocol,
    overload,
    runtime_checkable,
    AsyncGenerator,
    Callable,
    Awaitable,
)
from pathlib import Path

import logging
from enum import Enum
from expression import Error, Ok, Result
from pydantic import BaseModel, Field, model_validator
from contextlib import asynccontextmanager

from fp_ops.context import BaseContext

logger = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")
P = ParamSpec("P")

CoordinateType = Tuple[int, int]
MouseButtonLiteral = Literal["left", "middle", "right"]
WaitStateLiteral = Literal["visible", "hidden", "attached", "detached"]
NavigationWaitLiteral = Literal["load", "domcontentloaded", "networkidle"]


    


class MouseButton(Enum):
    """Enum representing mouse buttons for mouse actions"""

    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"

KeyModifierLiteral = Literal["alt", "control", "command", "shift"]
class KeyModifier(Enum):
    """Enum representing keyboard modifiers"""

    NONE = 0
    ALT = 1
    CTRL = 2
    COMMAND = 4
    SHIFT = 8

    @classmethod
    def combine(cls, modifiers: List["KeyModifier"]) -> int:
        """Combine multiple modifiers into a single value"""
        value = 0
        for modifier in modifiers:
            value |= modifier.value
        return value

class PointerEventType(Enum):
    """Enum representing pointer event types"""

    MOVE = "mouseMoved"
    DOWN = "mousePressed"
    UP = "mouseReleased"
    WHEEL = "mouseWheel"

class BaseInputOptions(BaseModel):
    """Base model for all operation options"""

    timeout: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True


class MouseOptions(BaseInputOptions):
    """Base options for mouse operations"""

    button: MouseButtonLiteral = "left"
    modifiers: List[KeyModifier] = Field(default_factory=list)
    steps: int = 1
    smooth: bool = True
    total_time: float = 0.5
    acceleration: float = 2.0
    force: float = 0.5
    move_to_center: bool = True
    click_count: int = 1
    delay_between_ms: Optional[int] = None
    position_offset: Optional[CoordinateType] = None

    @property
    def modifiers_value(self) -> int:
        """Get the combined value of all modifiers"""
        return KeyModifier.combine(self.modifiers)

class TypeOptions(BaseInputOptions):
    """Options for typing operations"""

    key: Optional[str] = None
    modifiers: List[KeyModifier] = Field(default_factory=list)
    delay: Optional[int] = None
    clear: bool = False

class SelectOptions(BaseInputOptions):
    """Options for select operations"""

    index: Optional[int] = None
    text: Optional[str] = None
    value: Optional[str] = None

class DragOptions(MouseOptions):
    """Options for drag operations"""

    source_offset: Optional[CoordinateType] = None
    target_offset: Optional[CoordinateType] = None
    steps: int = 1
    smooth: bool = True
    total_time: float = 0.5

class NavigationOptions(BaseInputOptions):
    """Options for navigation operations"""

    wait_until: NavigationWaitLiteral = "load"
    referer: Optional[str] = None

class WaitOptions(BaseInputOptions):
    """Options for wait operations"""

    state: WaitStateLiteral = "visible"
    poll_interval: int = 100

class BrowserOptions(BaseModel):
    """Configuration options for browser instances"""

    browser_type: Literal["chrome", "firefox", "edge", "chromium"] = "chromium"
    headless: bool = True
    timeout: int = 30000
    viewport_width: int = 1366
    viewport_height: int = 768
    navigation_timeout: Optional[int] = None
    wait_timeout: Optional[int] = None
    stealth_mode: bool = False
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    extra_http_headers: Dict[str, str] = Field(default_factory=dict)
    ignore_https_errors: bool = False
    disable_javascript: bool = False
    browser_args: List[str] = Field(default_factory=list)
    extra_args: Dict[str, Any] = Field(default_factory=dict)
    locale: Optional[str] = None
    timezone: Optional[str] = None
    remote_url: Optional[str] = None

    @model_validator(mode="after")
    def set_default_timeouts(self) -> "BrowserOptions":
        """Set default timeouts if not provided"""
        if self.navigation_timeout is None:
            self.navigation_timeout = self.timeout
        if self.wait_timeout is None:
            self.wait_timeout = self.timeout
        return self

ElementRef = TypeVar("ElementRef")

@runtime_checkable
class ElementHandle(Protocol, Generic[ElementRef]):
    """
    Uniform interface for browser elements.

    This protocol defines the contract that all browser element
    implementations must fulfill, regardless of the underlying automation library.

    Args:
        page_id: ID of the page containing this element for tracking purposes
        selector: The selector used to find this element (optional)
        element_ref: Reference to the element in the underlying automation library

    """
    driver: Driver
    page_id: str
    context_id: str
    selector: Optional[str]
    element_ref: ElementRef

    def get_page_id(self) -> str:
        """Get the page ID associated with this element"""
        return self.page_id

    def get_context_id(self) -> str:
        """Get the context ID associated with this element"""
        return self.context_id

    def get_selector(self) -> Optional[str]:
        """Get the selector used to find this element"""
        return self.selector

    def get_element_ref(self) -> ElementRef:
        """Get the reference to the element in the underlying automation library"""
        return self.element_ref

    async def click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Click the element."""
        ...

    async def double_click(
        self, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Double-click the element."""
        ...

    async def type(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Type text into the element."""
        ...

    async def fill(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Fill the element with text (replacing existing content)."""
        ...

    async def select(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        """Select an option from a dropdown/select element."""
        ...

    async def get_text(self) -> Result[str, Exception]:
        """Get element's text content."""
        ...

    async def text(self) -> str:
        """Get element's text content (simplified version)."""
        ...

    async def get_inner_text(self) -> Result[str, Exception]:
        """Get element's inner text (visible text only)."""
        ...

    async def get_html(self, outer: bool = True) -> Result[str, Exception]:
        """Get element's HTML content."""
        ...

    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        """Get element's attribute value."""
        ...

    async def attribute(self, name: str, default: str = "") -> str:
        """Get element's attribute value (simplified version)."""
        ...

    async def has_attribute(self, name: str) -> bool:
        """Check if element has the specified attribute."""
        ...

    async def get_property(self, name: str) -> Result[Any, Exception]:
        """Get element's JavaScript property value."""
        ...

    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        """Get element's bounding box (x, y, width, height)."""
        ...

    async def is_visible(self) -> Result[bool, Exception]:
        """Check if element is visible."""
        ...

    async def is_enabled(self) -> Result[bool, Exception]:
        """Check if element is enabled."""
        ...

    async def get_parent(self) -> Result[Optional["ElementHandle"], Exception]:
        """Get the parent element."""
        ...

    async def get_children(self) -> Result[List["ElementHandle"], Exception]:
        """Get all child elements."""
        ...

    async def query_selector(
        self, selector: str
    ) -> Result[Optional["ElementHandle"], Exception]:
        """Find a child element matching the selector."""
        ...

    async def query_selector_all(
        self, selector: str
    ) -> Result[List["ElementHandle"], Exception]:
        """Find all child elements matching the selector."""
        ...

    async def scroll_into_view(self) -> Result[None, Exception]:
        """Scroll the element into view."""
        ...

    async def input(
        self, text: str, options: Optional[TypeOptions] = None
    ) -> "ElementHandle":
        """Fill element with text and return self for chaining."""
        ...

    async def choose(
        self, value: Optional[str] = None, text: Optional[str] = None
    ) -> "ElementHandle":
        """Select an option and return self for chaining."""
        ...


    def as_native(self) -> ElementRef:
        """Get the native element reference."""
        ...

PageRef = TypeVar("PageRef")

@runtime_checkable
class Page(Protocol, Generic[PageRef]):
    """
    Uniform interface for browser pages/tabs.

    This protocol defines the contract that all browser page
    implementations must fulfill, regardless of the underlying automation library.
    """

    page_id: str
    page_ref: PageRef

    def get_page_id(self) -> str:
        """Get the page ID associated with this page"""
        return self.page_id

    async def goto(
        self, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate to a URL."""
        ...

    async def get_url(self) -> Result[str, Exception]:
        """Get the current URL."""
        ...

    async def current_url(self) -> Result[str, Exception]:
        """Get the current URL."""
        ...

    async def get_title(self) -> Result[str, Exception]:
        """Get the page title."""
        ...

    async def get_content(self) -> Result[str, Exception]:
        """Get the page HTML content."""
        ...

    async def get_page_source(self) -> Result[str, Exception]:
        """Get the HTML source of the page."""
        ...

    async def reload(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Reload the page."""
        ...

    async def go_back(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate back in history."""
        ...

    async def go_forward(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate forward in history."""
        ...

    async def query_selector(
        self, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """Find an element by selector."""
        ...

    async def query_selector_all(
        self, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        """Find all elements matching selector."""
        ...

    async def wait_for_selector(
        self, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        """Wait for an element matching the selector to appear."""
        ...

    async def wait_for_navigation(
        self, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Wait for navigation to complete."""
        ...

    async def click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Click an element identified by selector."""
        ...

    async def double_click(
        self, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Double-click an element identified by selector."""
        ...

    async def type(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Type text into an element identified by selector."""
        ...

    async def fill(
        self, selector: str, text: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Fill an element identified by selector with text."""
        ...

    async def select(
        self, selector: str, value: Optional[str] = None, text: Optional[str] = None
    ) -> Result[None, Exception]:
        """Select an option in a dropdown/select element."""
        ...

    async def execute_script(self, script: str, *args: Any) -> Result[Any, Exception]:
        """Execute JavaScript in the page."""
        ...

    @overload
    async def screenshot(self, path: Path) -> Result[Path, Exception]:
        """Take a screenshot of the page and save it to a file."""
        ...

    @overload
    async def screenshot(self) -> Result[bytes, Exception]:
        """Take a screenshot of the page."""
        ...

    async def screenshot(self, path: Optional[Path] = None) -> Result[Union[Path, bytes], Exception]:
        """Take a screenshot of the page, optionally saving to a file."""
        ...

    async def mouse_move(
        self, x: float, y: float, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Move the mouse to coordinates."""
        ...

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Press a mouse button."""
        ...

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Release a mouse button."""
        ...

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """Drag from source to target coordinates."""
        ...

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press a key."""
        ...

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press and hold a key."""
        ...

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Release a key."""
        ...

    async def close(self) -> Result[None, Exception]:
        """Close the page."""
        ...

    async def scroll(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
    ) -> Result[None, Exception]:
        """Scroll the page or an element into view."""
        ...

ContextRef = TypeVar("ContextRef")

class BrowserContextOptions(BaseModel):
    """Options for creating a browser context"""
    viewport: Optional[Dict[str, Any]] = None
    permissions: Optional[List[str]] = None
    user_agent: Optional[str] = None
    extra_http_headers: Optional[Dict[str, str]] = None
    proxy: Optional[Dict[str, Any]] = None
    user_data_dir: Optional[str] = None
    ignore_default_args: bool = False
    args: Optional[List[str]] = None
    headless: bool = True
    slow_mo: Optional[int] = None
    timeout: Optional[int] = None
    

@runtime_checkable
class BrowserContext(Protocol, Generic[ContextRef]):
    """
    Uniform interface for browser contexts.

    A browser context is an isolated browser session with its own cookies,
    localStorage, and cache.
    """

    page_id: str
    context_id: str
    context_ref: ContextRef

    def get_page_id(self) -> str:
        """Get the page ID associated with this context"""
        return self.page_id
    
    def get_context_id(self) -> str:
        """Get the context ID associated with this context"""
        return self.context_id

    async def new_page(self) -> Result[Page, Exception]:
        """Create a new page in this context."""
        ...

    async def create_page(
        self, nickname: Optional[str] = None
    ) -> Result[Page, Exception]:
        """Create a new page in this context."""
        ...

    async def pages(self) -> Result[List[Page], Exception]:
        """Get all pages in this context."""
        ...

    async def get_page(
        self, page_id: Optional[str] = None
    ) -> Result[Page, Exception]:
        """Get a page by ID or the default page."""
        ...

    async def close_page(
        self, page_id: Optional[str] = None
    ) -> Result[None, Exception]:
        """Close a page by ID or the default page."""
        ...

    async def get_cookies(self) -> Result[List[Dict[str, Any]], Exception]:
        """Get all cookies."""
        ...

    async def set_cookies(
        self, cookies: List[Dict[str, Any]]
    ) -> Result[None, Exception]:
        """Set cookies."""
        ...

    async def clear_cookies(self) -> Result[None, Exception]:
        """Clear all cookies."""
        ...

    async def add_init_script(self, script: str) -> Result[None, Exception]:
        """Add a script to be run in all pages."""
        ...

    async def set_content(self, content: str) -> Result[None, Exception]:
        """Set the content of the page."""
        ...

    async def mouse_move(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Move the mouse to coordinates."""
        ...

    async def mouse_down(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Press a mouse button."""
        ...

    async def mouse_up(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Release a mouse button."""
        ...

    async def mouse_click(
        self,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Click at the current mouse position."""
        ...

    async def mouse_double_click(
        self, x: int, y: int, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Double click at the specified coordinates."""
        ...

    async def mouse_drag(
        self,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """Drag from source to target coordinates."""
        ...

    async def key_press(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press a key."""
        ...

    async def key_down(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press and hold a key."""
        ...

    async def key_up(
        self, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Release a key."""
        ...

    async def close(self) -> Result[None, Exception]:
        """Close the context and all its pages."""
        ...

DriverRef = TypeVar("DriverRef")

@runtime_checkable
class Driver(Protocol, Generic[DriverRef]):
    """
    Uniform interface for browser automation drivers.

    This protocol defines the contract that all browser driver
    implementations must fulfill, regardless of the underlying automation library.
    """

    driver_ref: Optional[DriverRef] = None

    def get_driver_ref(self) -> Optional[DriverRef]:
        """Get the reference to the driver in the underlying automation library"""
        return self.driver_ref

    async def launch(
        self, options: Optional[BrowserOptions] = None
    ) -> Result[None, Exception]:
        """Launch the browser."""
        ...

    async def new_context(
        self, options: Optional[BrowserContextOptions] = None
    ) -> Result[BrowserContext, Exception]:
        """Create a new browser context."""
        ...

    async def create_context(
        self, options: Optional[BrowserContextOptions] = None
    ) -> Result[str, Exception]:
        """Create a new browser context with isolated storage and return its ID."""
        ...

    async def contexts(self) -> Result[List[BrowserContext], Exception]:
        """Get all browser contexts."""
        ...

    async def close_context(self, context_id: str) -> Result[None, Exception]:
        """Close a browser context."""
        ...

    async def create_page(self, context_id: str) -> Result[str, Exception]:
        """Create a new page in the specified context."""
        ...

    async def close_page(self, page_id: str) -> Result[None, Exception]:
        """Close a page."""
        ...

    async def goto(
        self, page_id: str, url: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Navigate a page to a URL."""
        ...

    async def current_url(self, page_id: str) -> Result[str, Exception]:
        """Get the current URL of a page."""
        ...

    async def get_source(self, page_id: str) -> Result[str, Exception]:
        """Get the current page HTML source."""
        ...

    async def screenshot(
        self, page_id: str, path: Optional[Path] = None
    ) -> Result[Union[Path, bytes], Exception]:
        """Take a screenshot of a page."""
        ...

    async def reload(self, page_id: str) -> Result[None, Exception]:
        """Reload the current page."""
        ...

    async def go_back(self, page_id: str) -> Result[None, Exception]:
        """Go back to the previous page."""
        ...

    async def go_forward(self, page_id: str) -> Result[None, Exception]:
        """Go forward to the next page."""
        ...

    async def query_selector(
        self, page_id: str, selector: str
    ) -> Result[Optional[ElementHandle], Exception]:
        """Query a single element with the provided selector in a page."""
        ...

    async def query_selector_all(
        self, page_id: str, selector: str
    ) -> Result[List[ElementHandle], Exception]:
        """Query all elements that match the provided selector in a page."""
        ...

    async def wait_for_selector(
        self, page_id: str, selector: str, options: Optional[WaitOptions] = None
    ) -> Result[Optional[ElementHandle], Exception]:
        """Wait for an element matching the selector to appear in a page."""
        ...

    async def wait_for_navigation(
        self, page_id: str, options: Optional[NavigationOptions] = None
    ) -> Result[None, Exception]:
        """Wait for navigation to complete in a page."""
        ...

    async def click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Click an element in a page."""
        ...

    async def double_click(
        self, page_id: str, selector: str, options: Optional[MouseOptions] = None
    ) -> Result[None, Exception]:
        """Double click an element in a page."""
        ...

    async def type(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """Type text into an element."""
        ...

    async def fill(
        self,
        page_id: str,
        selector: str,
        text: str,
        options: Optional[TypeOptions] = None,
    ) -> Result[None, Exception]:
        """Fill an input element with text."""
        ...

    async def select(
        self,
        page_id: str,
        selector: str,
        value: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Result[None, Exception]:
        """Select an option in a <select> element."""
        ...

    async def execute_script(
        self, page_id: str, script: str, *args: Any
    ) -> Result[Any, Exception]:
        """Execute JavaScript in the page context."""
        ...

    async def mouse_move(
        self,
        page_id: str,
        x: float,
        y: float,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Move the mouse to the specified coordinates within a context."""
        ...

    async def mouse_down(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Press a mouse button within a context."""
        ...

    async def mouse_up(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Release a mouse button within a context."""
        ...

    async def mouse_click(
        self,
        page_id: str,
        button: MouseButtonLiteral = "left",
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Click at the current mouse position within a context."""
        ...

    async def mouse_double_click(
        self,
        page_id: str,
        x: int,
        y: int,
        options: Optional[MouseOptions] = None,
    ) -> Result[None, Exception]:
        """Double click at the specified coordinates within a context."""
        ...

    async def mouse_drag(
        self,
        page_id: str,
        source: CoordinateType,
        target: CoordinateType,
        options: Optional[DragOptions] = None,
    ) -> Result[None, Exception]:
        """Drag from one element or position to another within a context."""
        ...

    async def key_press(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press a key or key combination within a context."""
        ...

    async def key_down(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Press and hold a key within a context."""
        ...

    async def key_up(
        self, page_id: str, key: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Release a key within a context."""
        ...

    async def get_element_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """Get the text content of an element."""
        ...

    async def get_element_attribute(
        self, page_id: str, element: ElementHandle, name: str
    ) -> Result[Optional[str], Exception]:
        """Get an attribute value from an element."""
        ...

    async def get_element_bounding_box(
        self, page_id: str, element: ElementHandle
    ) -> Result[Dict[str, float], Exception]:
        """Get the bounding box of an element."""
        ...

    async def click_element(
        self, page_id: str, element: ElementHandle
    ) -> Result[None, Exception]:
        """Click an element."""
        ...

    async def get_element_html(
        self, page_id: str, element: ElementHandle, outer: bool = True
    ) -> Result[str, Exception]:
        """Get the HTML content of an element."""
        ...

    async def get_element_inner_text(
        self, page_id: str, element: ElementHandle
    ) -> Result[str, Exception]:
        """Get the innerText of an element (visible text only)."""
        ...

    async def extract_table(
        self,
        page_id: str,
        table_element: ElementHandle,
        include_headers: bool = True,
        header_selector: str = "th",
        row_selector: str = "tr",
        cell_selector: str = "td",
    ) -> Result[List[Dict[str, str]], Exception]:
        """Extract data from an HTML table element."""
        ...

    async def scroll(
        self,
        page_id: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        selector: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Result[None, Exception]:
        """Scroll the page to specific coordinates or scroll an element into view."""
        ...

    async def execute_cdp_cmd(
        self, page_id: str, cmd: str, *args: Any
    ) -> Result[Any, Exception]:
        """Execute a CDP command."""
        ...

    async def close(self) -> Result[None, Exception]:
        """Close the browser and all its contexts."""
        ...

class RetryOptions(BaseModel):
    """Options for action retry behavior"""

    max_retries: int = 0
    retry_delay_ms: int = 500
    retry_on_error_types: List[str] = Field(default_factory=list)
    exponential_backoff: bool = False
    jitter: bool = True

class WaitUntilOptions(BaseModel):
    """Options for conditional waiting"""

    condition: str = ""
    timeout_ms: int = 30000
    poll_interval_ms: int = 100
    ignore_errors: bool = False

class ActionOptions(BaseModel):
    """Options for browser actions"""

    timeout_ms: int = 30000
    retry: RetryOptions = Field(default_factory=RetryOptions)
    wait: WaitUntilOptions = Field(default_factory=WaitUntilOptions)
    continue_on_error: bool = False
    record_performance: bool = False
    take_screenshot_on_error: bool = False
    validate_result: bool = False
    cleanup_after: bool = True

class ActionContext(BaseContext):
    """
    Context for browser automation actions.

    This context maintains references to the current driver,
    browser context, and page, allowing actions to interact
    with the browser in a uniform way.
    """

    driver: Optional[Driver] = Field(default=None, exclude=True)
    context: Optional[BrowserContext] = Field(default=None, exclude=True)
    page: Optional[Page] = Field(default=None, exclude=True)

    driver_type: str = "playwright"
    context_id: Optional[str] = None
    page_id: Optional[str] = None

    page_ids: Set[str] = Field(default_factory=set)

    retry_count: int = 0

    options: ActionOptions = Field(default_factory=ActionOptions)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def derive(self, **kwargs: Any) -> "ActionContext":
        """Create a new context with updated values."""
        new_metadata = None
        if "metadata" in kwargs:
            new_metadata = self.metadata.copy()
            metadata_updates = kwargs.pop("metadata")
            for key, value in metadata_updates.items():
                new_metadata[key] = value

        new_context = self.model_copy(update=kwargs)

        if new_metadata:
            new_context.metadata = new_metadata

        return new_context

    @property
    def current_url(self) -> Optional[str]:
        """Get the current URL from metadata."""
        return self.metadata.get("current_url")

    @property
    def has_active_page(self) -> bool:
        """Check if there's an active page."""
        return self.page is not None

    def with_retry_options(self, **retry_kwargs: Any) -> "ActionContext":
        """Update retry options and return new context."""
        new_retry = RetryOptions(**{**self.options.retry.model_dump(), **retry_kwargs})
        new_action_options = self.options.model_copy(update={"retry": new_retry})
        return self.derive(options=new_action_options)

    def with_timeout(self, timeout_ms: int) -> "ActionContext":
        """Set action timeout and return new context."""
        new_action_options = self.options.model_copy(update={"timeout_ms": timeout_ms})
        return self.derive(options=new_action_options)

    def increment_retry_count(self) -> "ActionContext":
        """Increment retry count and return new context."""
        return self.derive(retry_count=self.retry_count + 1)
