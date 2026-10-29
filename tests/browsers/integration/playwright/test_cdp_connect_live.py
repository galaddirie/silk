"""A real Chromium started outside Silk, driven over the DevTools Protocol."""

from __future__ import annotations

import asyncio
import subprocess
import threading
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fp_ops import _
from playwright.async_api import async_playwright

from silk.actions.navigation import Navigate as navigate
from silk.browsers.drivers import PlaywrightDriver
from silk.browsers.models import BrowserContextOptions, RequestBlocking
from silk.browsers.sessions import BrowserSession


async def _websocket_url(
    process: subprocess.Popen[bytes], profile: Path, log: Path
) -> str:
    """Chromium writes its DevTools port and browser path once it listens."""

    active_port = profile / "DevToolsActivePort"
    for _attempt in range(300):
        if process.poll() is not None:
            stderr = log.read_text(errors="replace")[-2000:]
            raise RuntimeError(f"Chromium exited ({process.returncode}): {stderr}")
        lines = active_port.read_text().splitlines() if active_port.exists() else []
        if len(lines) >= 2:
            return f"ws://127.0.0.1:{lines[0]}{lines[1]}"
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
    profile = tmp_path / "profile"
    log = tmp_path / "chromium.log"
    with log.open("wb") as stderr:
        process = subprocess.Popen(  # noqa: S603 - the trusted Playwright Chromium
            [
                executable,
                "--headless=new",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                # The flags Playwright itself launches Chromium with: no sandbox
                # (CI runners disallow it), and never touch the OS keychain.
                "--no-sandbox",
                "--no-first-run",
                "--use-mock-keychain",
                "--password-store=basic",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=stderr,
        )
        try:
            yield await _websocket_url(process, profile, log)
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
