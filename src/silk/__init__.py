"""
Silk - A flexible browser automation library
"""

__version__ = "0.1.1"

from expression import Ok, Error, Result, Option, Some, Nothing

from . import actions
from . import browsers
from . import models
from . import selectors

from .actions.decorators import action
