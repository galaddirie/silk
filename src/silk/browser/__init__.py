"""
Browser automation module for silk.

This module provides a unified interface for browser automation 
using different browser drivers.
"""
from silk.browser.driver import BrowserDriver, BrowserOptions, ElementHandle
from silk.browser.driver_factory import create_driver, DriverFactory

__all__ = [
    'BrowserDriver',
    'BrowserOptions',
    'ElementHandle',
    'create_driver',
    'DriverFactory',
] 