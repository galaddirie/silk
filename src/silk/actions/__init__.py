# pyright: strict
"""Typed unary browser actions grouped by browser, element, input, and navigation.

Public actions are PascalCase construction templates. Place exactly one direct
``fp_ops._`` in a supported positional operand, compose the returned operations,
and execute the pipeline explicitly with ``Operation.run``.  Page, context, and
element focus always travel through operation inputs and outputs.
"""

__all__: list[str] = []
