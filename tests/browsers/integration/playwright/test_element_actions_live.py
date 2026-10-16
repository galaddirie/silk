"""Live Chromium contracts for public element actions."""

from urllib.parse import quote

import pytest
from fp_ops import _

from silk.actions.elements import (
    WaitOptions,
    GetInnerText as get_inner_text,
    WaitForElement as wait_for_element,
)
from silk.actions.navigation import Navigate as navigate
from silk.browsers.sessions import BrowserSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wait_and_nested_query_actions_drive_live_chromium(
    browser_session: BrowserSession,
) -> None:
    page = browser_session.page
    document = quote(
        """
        <main id="root"></main>
        <script>
          setTimeout(() => {
            const item = document.createElement("div");
            item.id = "delayed-item";
            item.textContent = "ready";
            document.querySelector("#root").appendChild(item);
          }, 150);
        </script>
        """
    )

    navigated = await navigate(_, f"data:text/html,{document}").run(page)
    assert navigated.is_ok(), navigated
    result = await wait_for_element(
        "#delayed-item",
        _,
        options=WaitOptions(timeout=5_000, state="visible"),
    ).run(page)
    assert result.is_ok() and result.ok is not None
    assert (await result.ok.text()).ok == "ready"

    configured_page = await wait_for_element(
        _,
        page,
        options=WaitOptions(timeout=5_000, state="visible"),
    ).run("#delayed-item")
    assert configured_page.is_ok() and configured_page.ok is not None

    root = await wait_for_element(
        "#root",
        _,
        options=WaitOptions(timeout=5_000, state="visible"),
    ).run(page)
    assert root.is_ok() and root.ok is not None
    nested = await get_inner_text(_, root.ok).run("#delayed-item")
    assert nested.ok == "ready"
