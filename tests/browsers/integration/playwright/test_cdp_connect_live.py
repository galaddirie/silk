"""A real Chromium started outside Silk, driven over the DevTools Protocol."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import threading
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest
from fp_ops import _
from playwright.async_api import async_playwright

from silk.actions.navigation import Navigate as navigate
from silk.browsers.drivers import PlaywrightDriver
from silk.browsers.models import BrowserContextOptions, RequestBlocking
from silk.browsers.sessions import BrowserSession


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


async def _websocket_url(port: int) -> str:
    for _attempt in range(100):
        try:
            with urlopen(
                f"http://127.0.0.1:{port}/json/version", timeout=1
            ) as response:
                url: str = json.load(response)["webSocketDebuggerUrl"]
                return url
        except OSError:
            await asyncio.sleep(0.1)
    raise RuntimeError("Chromium never exposed its DevTools endpoint")


class _Ok(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = b"<title>ok</title>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        pass


@pytest.fixture
def site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Ok)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


@pytest.fixture
async def remote_chromium(tmp_path: Path) -> AsyncIterator[str]:
    """A headless Chromium process that Silk did not launch, like a cloud browser."""

    async with async_playwright() as playwright:
        executable = playwright.chromium.executable_path
    port = _free_port()
    process = subprocess.Popen(  # noqa: S603 - the trusted Playwright Chromium binary
        [
            executable,
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={tmp_path / 'profile'}",
            "--no-first-run",
            # Playwright's own launch flags: never touch the OS keychain.
            "--use-mock-keychain",
            "--password-store=basic",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield await _websocket_url(port)
    finally:
        process.terminate()
        process.wait(timeout=10)


FETCH = "((path) => fetch(path).then(() => 'loaded', () => 'blocked'))"


@pytest.mark.asyncio
async def test_session_drives_the_remote_default_context(
    remote_chromium: str, site: str
) -> None:
    options = BrowserContextOptions(
        timeout=5_000,
        blocking=RequestBlocking(url_patterns=("*/blocked",)),
    )
    async with BrowserSession(
        context_options=options,
        driver=PlaywrightDriver(cdp_url=remote_chromium),
    ) as session:
        native_context = session.context.native  # type: ignore[attr-defined]
        assert native_context is native_context.browser.contexts[0]

        page = session.page
        assert (await navigate(_, f"{site}/").run(page)).is_ok()
        allowed = await page.evaluate(f"{FETCH}('/allowed')")
        blocked = await page.evaluate(f"{FETCH}('/blocked')")

    assert allowed.ok == "loaded"
    assert blocked.ok == "blocked"
