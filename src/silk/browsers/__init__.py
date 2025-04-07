"""
Browser automation module for silk.

This module provides a unified interface for browser automation 
using different browser drivers.
"""
# Fix circular import by importing each class from its source file
from silk.browsers.driver import BrowserDriver, BrowserOptions
from silk.browsers.element import ElementHandle
from silk.browsers.driver_factory import create_driver, DriverFactory

__all__ = [
    'BrowserDriver',
    'BrowserOptions',
    'ElementHandle',
    'create_driver',
    'DriverFactory',
] 