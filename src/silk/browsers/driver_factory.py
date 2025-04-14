"""
Driver factory module for creating browser driver instances based on available dependencies.
"""

from importlib import import_module
from typing import Literal, Optional, TypeVar, cast

from silk.browsers.driver import BrowserDriver, BrowserOptions

T = TypeVar("T")

ValidDriverTypes = Literal["playwright"]


class DriverFactory:
    """Factory for creating browser driver instances"""

    @staticmethod
    def create_driver(
        driver_type: ValidDriverTypes, options: Optional[BrowserOptions] = None
    ) -> BrowserDriver:
        """
        Create a browser driver instance of the specified type.

        Args:
            driver_type: Type of driver to create ('playwright')
            options: Browser options (will use defaults if None)

        Returns:
            An instance of the requested browser driver

        Raises:
            ImportError: If the required dependencies for the driver are not installed
            ValueError: If an unknown driver type is specified
        """
        options = options or BrowserOptions()

        driver_classes = {
            "playwright": ("silk.browsers.drivers.playwright", "PlaywrightDriver"),
        }

        if driver_type not in driver_classes:
            raise ValueError(
                f"Unknown driver type: {driver_type}. Available types: {', '.join(driver_classes.keys())}"
            )

        module_name, class_name = driver_classes[driver_type]

        try:
            module = import_module(module_name)
            driver_class = getattr(module, class_name)
            return cast(BrowserDriver, driver_class(options))
        except ImportError as e:
            package_names = {
                "playwright": "playwright",
                "patchright": "patchright",
                "selenium": "selenium",
                "puppeteer": "pyppeteer",
            }
            package = package_names.get(driver_type, driver_type)
            raise ImportError(
                f"package: {package}"
                f"Could not import {driver_type} driver. "
                f"To use this driver, install silk. with the {driver_type} extra: "
                f"pip install silk.[{driver_type}]"
            ) from e


def create_driver(
    driver_type: ValidDriverTypes, options: Optional[BrowserOptions] = None
) -> BrowserDriver:
    """Shorthand function to create a browser driver instance"""
    return DriverFactory.create_driver(driver_type, options)
