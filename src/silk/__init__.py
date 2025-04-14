"""
Silk - A flexible browser automation library
"""

__version__ = "0.1.6"

from expression import Error, Nothing, Ok, Option, Result, Some  # noqa
from fp_ops import operation  # noqa

__all__ = ["operation", "Error", "Nothing", "Ok", "Option", "Result", "Some"]
