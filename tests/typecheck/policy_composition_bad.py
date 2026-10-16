# pyright: strict
"""Policy compositions that strict type checkers must reject."""

from fp_ops import (
    Operation,
    Result,
    _,
    fanout_all_settled,
    fanout_parallel,
    retry,
    traverse_all_settled,
    traverse_parallel,
)

from silk.actions.browser import (
    CloseContext as close_context,
    ClosePage as close_page,
    NewPage as new_page,
)
from silk.actions.navigation import (
    CurrentUrl as current_url,
    Navigate as navigate,
    Title as title,
)
from silk.browsers.models import BrowserContext, Page


async def incompatible_policy_outputs(
    page: Page,
    context: BrowserContext,
) -> None:
    # typecheck-case: policy_composition.001
    retry(current_url(_), attempts=2).then(close_page(_))
    # typecheck-case: policy_composition.002
    fanout_parallel(current_url(_), title(_)).then(current_url(_))
    # typecheck-case: policy_composition.003
    traverse_parallel(current_url(_), limit=2).then(current_url(_))
    # typecheck-case: policy_composition.004
    traverse_all_settled(current_url(_), limit=2).then(navigate(_, "/next"))

    # typecheck-case: policy_composition.005
    await retry(current_url(_), attempts=2).run(context)
    # typecheck-case: policy_composition.006
    await traverse_parallel(new_page(_), limit=2).run([page])


def wrong_declared_policy_types() -> None:
    # typecheck-case: policy_composition.007
    one_value: Operation[Page, tuple[str]] = fanout_parallel(current_url(_), title(_))
    # typecheck-case: policy_composition.008
    unwrapped: Operation[Page, tuple[str, str]] = fanout_all_settled(
        current_url(_), title(_)
    )
    # typecheck-case: policy_composition.009
    wrong_settled: Operation[
        Page,
        tuple[Result[int, Exception], Result[str, Exception]],
    ] = fanout_all_settled(current_url(_), title(_))
    del one_value, unwrapped, wrong_settled


def incompatible_shared_fanout_input() -> None:
    # typecheck-case: policy_composition.010
    fanout_parallel(current_url(_), new_page(_)).run("neither page nor context")
    # typecheck-case: policy_composition.011
    new_page(_).then(close_context(_)).then(close_page(_))
