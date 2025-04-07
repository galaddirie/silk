from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    ParamSpec,
    Tuple,
    TypeVar,
)

if TYPE_CHECKING:
    from silk.browsers.context import BrowserPage
    from silk.browsers.manager import BrowserManager
    from silk.browsers.driver import BrowserDriver

import logging
from enum import Enum

from expression.core import Error, Ok, Result
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")
P = ParamSpec("P")

CoordinateType = Tuple[int, int]
MouseButtonLiteral = Literal["left", "middle", "right"]
WaitStateLiteral = Literal["visible", "hidden", "attached", "detached"]
NavigationWaitLiteral = Literal["load", "domcontentloaded", "networkidle"]


class ActionContext:
    """
    Action context for action execution containing references to browser context and page
    instead of direct driver references.
    """

    def __init__(
        self,
        browser_manager: Optional["BrowserManager"] = None,
        context_id: Optional[str] = None,
        page_id: Optional[str] = None,
        retry_count: int = 0,
        max_retries: int = 0,
        retry_delay_ms: int = 0,
        timeout_ms: int = 0,
        parent_context: Optional["ActionContext"] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.browser_manager = browser_manager
        self.context_id = context_id
        self.page_id = page_id
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.timeout_ms = timeout_ms
        self.parent_context = parent_context
        self.metadata = metadata or {}

    async def get_page(self) -> Result["BrowserPage", Exception]:
        """Get the browser page for this context"""
        if not self.browser_manager or not self.context_id or not self.page_id:
            return Error(
                Exception(
                    "ActionContext missing required browser_manager, context_id, or page_id"
                )
            )

        context_result = self.browser_manager.get_context(self.context_id)
        if context_result.is_error():
            return Error(context_result.error)

        context = context_result.default_value(None)
        if not context:
            return Error(Exception("No context found"))

        return context.get_page(self.page_id)

    async def get_driver(self) -> Result["BrowserDriver", Exception]:
        """Get the underlying driver (for specific use cases only)"""
        if not self.browser_manager or not self.context_id:
            return Error(
                Exception(
                    "ActionContext missing required browser_manager or context_id"
                )
            )

        driver = self.browser_manager.drivers.get(self.context_id)
        if not driver:
            return Error(Exception(f"No driver found for context ID {self.context_id}"))

        return Ok(driver)

    # todo add interface for derived context
    def derive(self, **kwargs: Any) -> "ActionContext":
        """Create a new context derived from this one with some values changed"""
        new_context = ActionContext(
            browser_manager=kwargs.get("browser_manager", self.browser_manager),
            context_id=kwargs.get("context_id", self.context_id),
            page_id=kwargs.get("page_id", self.page_id),
            retry_count=kwargs.get("retry_count", self.retry_count),
            max_retries=kwargs.get("max_retries", self.max_retries),
            retry_delay_ms=kwargs.get("retry_delay_ms", self.retry_delay_ms),
            timeout_ms=kwargs.get("timeout_ms", self.timeout_ms),
            parent_context=kwargs.get("parent_context", self),
            metadata={**self.metadata, **(kwargs.get("metadata", {}))},
        )
        return new_context


class MouseButton(Enum):
    """Enum representing mouse buttons for mouse actions"""

    LEFT = "left"
    MIDDLE = "middle"
    RIGHT = "right"


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


class BaseOptions(BaseModel):
    """Base model for all operation options"""

    timeout: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True


class MouseOptions(BaseOptions):
    """Base options for mouse operations"""

    button: MouseButtonLiteral = "left"
    modifiers: List[KeyModifier] = Field(default_factory=list)

    @property
    def modifiers_value(self) -> int:
        """Get the combined value of all modifiers"""
        return KeyModifier.combine(self.modifiers)


class ClickOptions(MouseOptions):
    """Options for click operations"""

    click_count: int = 1
    delay_between_ms: Optional[int] = None
    position_offset: Optional[CoordinateType] = None


class KeyPressOptions(MouseOptions):
    """Options for key press operations"""

    key: str
    modifiers: List[KeyModifier] = Field(default_factory=list)


class TypeOptions(BaseOptions):
    """Options for typing operations"""

    delay: Optional[int] = None
    clear: bool = False


class MouseMoveOptions(BaseOptions):
    """Options for mouse movement operations"""

    steps: int = 1
    smooth: bool = True
    total_time: float = 0.5
    acceleration: float = 2.0


class DragOptions(MouseOptions):
    """Options for drag operations"""

    source_offset: Optional[CoordinateType] = None
    target_offset: Optional[CoordinateType] = None
    steps: int = 1
    smooth: bool = True
    total_time: float = 0.5


class NavigationOptions(BaseOptions):
    """Options for navigation operations"""

    wait_until: NavigationWaitLiteral = "load"
    referer: Optional[str] = None


class WaitOptions(BaseOptions):
    """Options for wait operations"""

    state: WaitStateLiteral = "visible"
    poll_interval: int = 100


class BrowserOptions(BaseModel):
    """Configuration options for browser instances"""

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

    @model_validator(mode="after")
    def set_default_timeouts(self) -> "BrowserOptions":
        """Set default timeouts if not provided"""
        if self.navigation_timeout is None:
            self.navigation_timeout = self.timeout
        if self.wait_timeout is None:
            self.wait_timeout = self.timeout
        return self
