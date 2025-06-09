"""
Text manipulation operations for Silk.
"""
from fp_ops.text import (
    split,
    join,
    replace,
    to_lower,
    to_upper,
    strip,
    lstrip,
    rstrip,
    capitalize,
    title,
    starts_with,
    ends_with,
    contains,
    match,
    search,
    find_all,
    sub,
    is_alpha,
    is_numeric,
    is_alphanumeric,
    is_whitespace,
    is_upper,
    is_lower,
)



__all__ = [
    # Basic String Operations
    "split",
    "join",
    "replace",
    "to_lower",
    "to_upper",
    "strip",
    "lstrip",
    "rstrip",
    # Case Conversions
    "capitalize",
    "title",
    # String Checks
    "starts_with",
    "ends_with",
    "contains",
    # Pattern Matching
    "match",
    "search",
    "find_all",
    "sub",
    # String Validation
    "is_alpha",
    "is_numeric",
    "is_alphanumeric",
    "is_whitespace",
    "is_upper",
    "is_lower",
] 