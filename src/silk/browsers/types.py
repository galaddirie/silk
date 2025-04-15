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
from expression import Error, Ok, Result
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

# TODO unifiy click options and mouse options
class MouseOptions(BaseOptions):
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



    

class TypeOptions(BaseOptions):
    """Options for typing operations"""
    key: Optional[str] = None
    modifiers: List[KeyModifier] = Field(default_factory=list)
    delay: Optional[int] = None
    clear: bool = False

class SelectOptions(BaseOptions):
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
    remote_url: Optional[str] = None  # URL for connecting to a remote CDP browser


    @model_validator(mode="after")
    def set_default_timeouts(self) -> "BrowserOptions":
        """Set default timeouts if not provided"""
        if self.navigation_timeout is None:
            self.navigation_timeout = self.timeout
        if self.wait_timeout is None:
            self.wait_timeout = self.timeout
        return self
