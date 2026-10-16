"""Nominal browser focus, session lifecycle, and immutable configuration."""

from silk.browsers.capabilities import (
    BROWSER_OPTIONS,
    BROWSER_SESSION,
    DRIVER,
    BrowserDriverCapability,
    BrowserOptionsCapability,
    BrowserSessionInfo,
    BrowserSessionNotStartedError,
)
from silk.browsers.models import (
    BrowserContext,
    BrowserContextOptions,
    BrowserFocus,
    BrowserHttpHeaders,
    BrowserLaunchProxy,
    BrowserOptions,
    BrowserProxy,
    BrowserViewport,
    ElementHandle,
    KeyModifier,
    Page,
)
from silk.browsers.sessions import BrowserSession, BrowserSessionCleanupError

__all__ = [
    "BROWSER_OPTIONS",
    "BROWSER_SESSION",
    "DRIVER",
    "BrowserContext",
    "BrowserContextOptions",
    "BrowserDriverCapability",
    "BrowserFocus",
    "BrowserHttpHeaders",
    "BrowserLaunchProxy",
    "BrowserOptions",
    "BrowserOptionsCapability",
    "BrowserProxy",
    "BrowserSession",
    "BrowserSessionCleanupError",
    "BrowserSessionInfo",
    "BrowserSessionNotStartedError",
    "BrowserViewport",
    "ElementHandle",
    "KeyModifier",
    "Page",
]
