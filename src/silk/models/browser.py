from abc import ABC, abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
    ParamSpec,
)
from enum import Enum, auto
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from expression.core import Result, Ok, Error, Option, Some, Nothing
import asyncio

# Type variables for generics
T = TypeVar("T")
S = TypeVar("S")
R = TypeVar("R")
P = ParamSpec("P")

# Common type definitions
CoordinateType = Tuple[int, int]
MouseButtonLiteral = Literal["left", "middle", "right"]
WaitStateLiteral = Literal["visible", "hidden", "attached", "detached"]
NavigationWaitLiteral = Literal["load", "domcontentloaded", "networkidle"]


from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ActionContext(BaseModel):
    """ActionContext for action execution with metadata and configuration"""

    retry_count: int = 0
    max_retries: int = 3
    retry_delay_ms: int = 500
    timeout_ms: Optional[int] = None
    parent_context: Optional["ActionContext"] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    browser_context_id: Optional[str] = None
    page_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


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

    @field_validator("navigation_timeout", mode="before")
    def set_navigation_timeout(
        cls, v: Optional[int], info: Dict[str, Any]
    ) -> Optional[int]:
        """Set default navigation timeout if not provided"""
        if v is None:
            return info.data.get("timeout")
        return v

    @field_validator("wait_timeout", mode="before")
    def set_wait_timeout(cls, v: Optional[int], info: Dict[str, Any]) -> Optional[int]:
        """Set default wait timeout if not provided"""
        if v is None:
            return info.data.get("timeout")
        return v


class ElementHandle(Protocol):
    """Protocol defining the interface for browser element handles"""

    @abstractmethod
    async def click(
        self, options: Optional[ClickOptions] = None
    ) -> Result[None, Exception]:
        """Click the element"""
        pass

    @abstractmethod
    async def fill(
        self, value: str, options: Optional[TypeOptions] = None
    ) -> Result[None, Exception]:
        """Fill the element with text"""
        pass

    @abstractmethod
    async def get_text(self) -> Result[str, Exception]:
        """Get the text content of the element"""
        pass

    @abstractmethod
    async def get_attribute(self, name: str) -> Result[Optional[str], Exception]:
        """Get attribute value from the element"""
        pass

    @abstractmethod
    async def is_visible(self) -> Result[bool, Exception]:
        """Check if the element is visible"""
        pass

    @abstractmethod
    async def get_bounding_box(self) -> Result[Dict[str, float], Exception]:
        """Get the element's bounding box (x, y, width, height)"""
        pass
