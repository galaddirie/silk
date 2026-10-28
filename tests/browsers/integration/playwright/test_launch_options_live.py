"""Real Chromium probes for every meaningful launch setting."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest
from fp_ops import _

from silk.actions.navigation import (
    Evaluate as evaluate,
    Navigate as navigate,
    Title as title,
)
from silk.browsers.drivers import PlaywrightDriver
from silk.browsers.models import (
    BrowserDriver,
    BrowserOptions,
    BrowserProxy,
    LaunchedBrowser,
)
from silk.browsers.sessions import BrowserSession


@dataclass
class LaunchProxy:
    server: str
    requests: list[bytes] = field(default_factory=list)


@asynccontextmanager
async def launch_proxy() -> AsyncIterator[LaunchProxy]:
    requests: list[bytes] = []

    async def respond(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            requests.append(request)
            body = b"<title>launch proxy reached</title>"
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
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
        yield LaunchProxy(
            server=f"http://127.0.0.1:{port}",
            requests=requests,
        )
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_launch_honors_headless_timeout_and_args() -> None:
    async with BrowserSession(
        options=BrowserOptions(
            headless=True,
            timeout=10_000,
            args=("--js-flags=--expose-gc",),
        ),
    ) as session:
        exposed = await evaluate(_, "() => typeof gc").run(session.page)
        assert exposed.is_ok(), exposed
        assert exposed.ok == "function"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_session_rejects_repeated_start_and_can_restart() -> None:
    session = BrowserSession(options=BrowserOptions(headless=True, timeout=10_000))
    assert await session.start() is session

    try:
        with pytest.raises(RuntimeError, match="already started"):
            await session.start()

        await session.close()
        assert await session.start() is session
    finally:
        await session.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_launch_honors_the_typed_proxy_endpoint() -> None:
    async with launch_proxy() as proxy:
        async with BrowserSession(
            options=BrowserOptions(
                headless=True,
                timeout=10_000,
                proxy=BrowserProxy(server=proxy.server),
            ),
        ) as session:
            navigated = await navigate(
                _,
                "http://silk-launch-proxy.invalid/launch",
            ).run(session.page)
            assert navigated.is_ok(), navigated
            assert any(
                request.startswith(b"GET http://silk-launch-proxy.invalid/launch")
                for request in proxy.requests
            )
            page_title = await title(_).run(session.page)
            assert page_title.is_ok(), page_title
            assert page_title.ok == "launch proxy reached"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_session_runs_pipelines_through_a_wrapping_custom_driver() -> None:
    launched: list[BrowserOptions] = []

    class RecordingDriver(BrowserDriver):
        async def launch(self, options: BrowserOptions) -> LaunchedBrowser:
            launched.append(options)
            return await PlaywrightDriver(browser_type="chromium").launch(options)

    options = BrowserOptions(headless=True, timeout=10_000)
    async with BrowserSession(options=options, driver=RecordingDriver()) as session:
        script = "() => document.title = 'custom driver'"
        evaluated = await evaluate(_, script).run(session.page)
        assert evaluated.is_ok(), evaluated
        page_title = await title(_).run(session.page)
        assert page_title.is_ok(), page_title
        assert page_title.ok == "custom driver"

    assert launched == [options]
