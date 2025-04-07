"""
silk - A flexible browser automation library with support for multiple drivers
"""

__version__ = "0.1.0"

# Export main components for easier imports
from expression import Ok, Error, Result, Option, Some, Nothing

# Import main modules
from . import actions
from . import browsers
from . import models
from . import selectors

# Export commonly used decorators and functions
from .actions.decorators import action
