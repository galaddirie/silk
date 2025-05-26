"""
Browser automation module for silk.

This module provides a unified interface for browser automation
using different browser drivers.
"""

from silk.browsers.models import (
    ActionContext,
    ActionOptions,
    BaseInputOptions,
    BrowserContext,
    BrowserOptions,
    CoordinateType,
    DragOptions,
    Driver,
    ElementHandle,
    KeyModifier,
    MouseButton,
    MouseButtonLiteral,
    MouseOptions,
    NavigationOptions,
    NavigationWaitLiteral,
    Page,
    PointerEventType,
    RetryOptions,
    SelectOptions,
    TypeOptions,
    WaitOptions,
    WaitStateLiteral,
    WaitUntilOptions,
)
from silk.browsers.sessions import BrowserSession

__all__ = [
    "ActionContext",
    "ActionOptions",
    "BaseInputOptions",
    "BrowserContext",
    "BrowserOptions",
    "BrowserSession",
    "CoordinateType",
    "DragOptions",
    "Driver",
    "ElementHandle",
    "KeyModifier",
    "MouseButton",
    "MouseButtonLiteral",
    "MouseOptions",
    "NavigationOptions",
    "NavigationWaitLiteral",
    "Page",
    "PointerEventType",
    "RetryOptions",
    "SelectOptions",
    "TypeOptions",
    "WaitOptions",
    "WaitStateLiteral",
    "WaitUntilOptions",
]
