"""
Silk - A flexible browser automation library
"""

__version__ = "0.2.5"

from expression import Error, Nothing, Ok, Option, Result, Some  # noqa
from fp_ops import operation  # noqa

__all__ = ["operation", "Error", "Nothing", "Ok", "Option", "Result", "Some"]
