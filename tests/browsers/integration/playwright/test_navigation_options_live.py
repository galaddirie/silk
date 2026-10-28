"""Real Chromium proof for URL-navigation-only configuration."""

from __future__ import annotations

import asyncio
from urllib.parse import quote

import pytest
from fp_ops import _

from silk.actions.navigation import (
    CurrentUrl as current_url,
    Navigate as navigate,
    NavigateOptions,
    NavigationOptions,
    WaitForNavigation as wait_for_navigation,
)
from silk.browsers.models import BrowserOptions
from silk.browsers.sessions import BrowserSession


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_sends_the_configured_navigation_referer() -> None:
    requests: list[bytes] = []

    async def respond(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            requests.append(request)
            body = b"<title>referer observed</title>"
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                + f"Content-Length: {len(body)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + body
            )
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(respond, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    try:
        async with BrowserSession(
            options=BrowserOptions(headless=True, timeout=10_000)
        ) as session:
            navigated = await navigate(
                _,
                f"http://127.0.0.1:{port}/target",
                options=NavigateOptions(
                    timeout=5_000,
                    wait_until="domcontentloaded",
                    referer="https://referrer.test/source",
                ),
            ).run(session.page)
            assert navigated.is_ok(), navigated
            assert any(
                b"referer: https://referrer.test/source" in request.lower()
                for request in requests
            )
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_wait_for_navigation_awaits_the_next_main_frame_navigation() -> None:
    async with BrowserSession(
        options=BrowserOptions(headless=True, timeout=10_000)
    ) as session:
        page = session.page
        target_url = "data:text/html," + quote(
            "<title>Delayed navigation</title><main>arrived</main>"
        )

        async def navigate_later() -> None:
            await asyncio.sleep(0.3)
            navigated = await navigate(_, target_url).run(page)
            assert navigated.is_ok(), navigated

        trigger = asyncio.create_task(navigate_later())
        waited = await wait_for_navigation(
            _,
            options=NavigationOptions(
                timeout=5_000,
                wait_until="domcontentloaded",
            ),
        ).run(page)
        returned_url = await current_url(_).run(page)
        await trigger

        assert waited.is_ok(), waited
        assert waited.ok is page
        assert returned_url.is_ok(), returned_url
        assert returned_url.ok == target_url
