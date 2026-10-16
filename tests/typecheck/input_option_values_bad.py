# pyright: strict
"""Calls strict checkers must reject for input-option value objects."""

from silk.actions.input import (
    ClickOptions,
    DoubleClickOptions,
    DragOptions,
    FillOptions,
    TypeTextOptions,
)
from silk.browsers.models import KeyModifier

# typecheck-case: input_option_values.001
ClickOptions(timeout_ms="100")
# typecheck-case: input_option_values.002
ClickOptions(delay_ms=1.5)
# typecheck-case: input_option_values.003
ClickOptions(button="bogus")
# typecheck-case: input_option_values.004
ClickOptions(modifiers=[KeyModifier.ALT])
# typecheck-case: input_option_values.005
ClickOptions(click_count="two")
# typecheck-case: input_option_values.006
ClickOptions(force="yes")
# typecheck-case: input_option_values.007
DoubleClickOptions(button="bogus")
# typecheck-case: input_option_values.008
DoubleClickOptions(modifiers=("alt",))
# typecheck-case: input_option_values.009
DoubleClickOptions(delay_ms=1.5)
# typecheck-case: input_option_values.010
DoubleClickOptions(force="yes")
# typecheck-case: input_option_values.011
FillOptions(timeout_ms="100")
# typecheck-case: input_option_values.012
FillOptions(clear="yes")
# typecheck-case: input_option_values.013
TypeTextOptions(timeout_ms="100")
# typecheck-case: input_option_values.014
TypeTextOptions(delay_ms=1.5)
# typecheck-case: input_option_values.015
DragOptions(steps="many")
# typecheck-case: input_option_values.016
DragOptions(move_to_center="yes")
# typecheck-case: input_option_values.017
DragOptions(position_offset=[1, 2])
# typecheck-case: input_option_values.018
DragOptions(position_offset=(1,))
# typecheck-case: input_option_values.019
DragOptions(source_offset=(1.0, 2))
# typecheck-case: input_option_values.020
DragOptions(target_offset=(1, "2"))

click_options = ClickOptions()
drag_options = DragOptions()
# typecheck-case: input_option_values.021
click_options.force = True
# typecheck-case: input_option_values.022
drag_options.steps = 2
