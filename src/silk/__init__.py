"""
Silk - A flexible browser automation library
"""

__version__ = "0.3.1"

from expression import Error, Nothing, Ok, Option, Result, Some  # noqa
from fp_ops import operation, Operation  # noqa

__all__ = ["operation", "Operation", "Error", "Nothing", "Ok", "Option", "Result", "Some"]
