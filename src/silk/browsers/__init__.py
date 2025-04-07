"""
Browser automation module for silk.

This module provides a unified interface for browser automation
using different browser drivers.
"""

from silk.browsers.driver import BrowserDriver, BrowserOptions
from silk.browsers.driver_factory import DriverFactory, create_driver
from silk.browsers.element import ElementHandle

__all__ = [
    "BrowserDriver",
    "BrowserOptions",
    "ElementHandle",
    "create_driver",
    "DriverFactory",
]
