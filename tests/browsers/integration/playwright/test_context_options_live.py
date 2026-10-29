"""Real Chromium probes for every public browser-context option."""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from silk.browsers.models import (
    BROWSER,
    BrowserContextOptions,
    BrowserOptions,
    BrowserProxy,
    BrowserViewport,
)
from silk.browsers.sessions import BrowserSession
from silk.errors import BrowserTimeoutError


@dataclass
class LocalResponseServer:
    url: str
    requests: list[bytes] = field(default_factory=list)
    proxy_authorization_seen: asyncio.Event = field(default_factory=asyncio.Event)


@asynccontextmanager
async def local_response_server(
    *,
    body: bytes,
    required_proxy_authorization: bytes | None = None,
    response_gate: asyncio.Event | None = None,
    ssl_context: ssl.SSLContext | None = None,
) -> AsyncIterator[LocalResponseServer]:
    observed: list[bytes] = []
    authorization_seen = asyncio.Event()
    handler_tasks: set[asyncio.Task[None]] = set()

    async def respond(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            observed.append(request)
            if response_gate is not None:
                await response_gate.wait()
            authorization = (
                b"proxy-authorization: " + (required_proxy_authorization or b"").lower()
            )
            if (
                required_proxy_authorization is not None
                and authorization in request.lower()
            ):
                authorization_seen.set()
            if (
                required_proxy_authorization is not None
                and authorization not in request.lower()
            ):
                writer.write(
                    b"HTTP/1.1 407 Proxy Authentication Required\r\n"
                    b'Proxy-Authenticate: Basic realm="Silk"\r\n'
                    b"Content-Length: 0\r\n"
                    b"Connection: close\r\n\r\n"
                )
            else:
                writer.write(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html; charset=utf-8\r\n"
                    + f"Content-Length: {len(body)}\r\n".encode()
                    + b"Connection: close\r\n\r\n"
                    + body
                )
            with suppress(ConnectionError):
                await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def track_handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            handler_tasks.add(task)
        try:
            await respond(reader, writer)
        finally:
            if task is not None:
                handler_tasks.discard(task)

    server = await asyncio.start_server(
        track_handler,
        "127.0.0.1",
        0,
        ssl=ssl_context,
    )
    socket = server.sockets[0]
    port = socket.getsockname()[1]
    probe = LocalResponseServer(
        url=(
            f"{'https' if ssl_context is not None else 'http'}://"
            f"127.0.0.1:{port}/context-options"
        ),
        requests=observed,
        proxy_authorization_seen=authorization_seen,
    )
    try:
        yield probe
    finally:
        if response_gate is not None:
            response_gate.set()
        server.close()
        await server.wait_closed()
        if handler_tasks:
            await asyncio.gather(*tuple(handler_tasks), return_exceptions=True)


def self_signed_server_context() -> ssl.SSLContext:
    fixtures = Path(__file__).with_name("fixtures")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(
        certfile=fixtures / "localhost-cert.pem",
        keyfile=fixtures / "localhost-key.pem",
    )
    return context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_honors_non_proxy_context_options() -> None:
    body = b"<title>context options</title><main>configured</main>"
    async with local_response_server(body=body) as server:
        async with BrowserSession(
            options=BrowserOptions(headless=True, timeout=10_000),
            context_options=BrowserContextOptions(
                viewport=BrowserViewport(width=913, height=617),
                permissions=("geolocation",),
                user_agent="SilkContextProbe/1.0",
                extra_http_headers={"x-silk-context": "configured"},
                locale="fr-CA",
                timezone_id="America/Toronto",
                timeout=180,
            ),
        ) as session:
            page = session.page
            navigated = await page.navigate(server.url)
            assert navigated.is_ok(), navigated

            browser_state = await page.evaluate(
                """() => ({
                    width: window.innerWidth,
                    height: window.innerHeight,
                    userAgent: navigator.userAgent,
                    locale: navigator.language,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                })"""
            )
            assert browser_state.is_ok(), browser_state
            assert browser_state.ok == {
                "width": 913,
                "height": 617,
                "userAgent": "SilkContextProbe/1.0",
                "locale": "fr-CA",
                "timezone": "America/Toronto",
            }

            permission = await page.evaluate(
                """async () => (
                    await navigator.permissions.query({name: "geolocation"})
                ).state"""
            )
            assert permission.is_ok(), permission
            assert permission.ok == "granted"
            assert any(
                b"x-silk-context: configured" in request.lower()
                for request in server.requests
            )

            timed_out = await page.wait_for_selector("#never-present")
            assert timed_out.is_error()
            assert isinstance(timed_out.error, BrowserTimeoutError)
            assert isinstance(timed_out.error.__cause__, PlaywrightTimeoutError)
            assert "180ms" in str(timed_out.error)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_honors_the_context_navigation_timeout() -> None:
    release_response = asyncio.Event()

    async with local_response_server(
        body=b"<main>too late</main>",
        response_gate=release_response,
    ) as server:
        async with BrowserSession(
            options=BrowserOptions(headless=True, timeout=10_000),
            context_options=BrowserContextOptions(navigation_timeout=80),
        ) as session:
            timed_out = await session.page.navigate(server.url)
            assert timed_out.is_error(), timed_out
            assert isinstance(timed_out.error, BrowserTimeoutError)
            assert isinstance(timed_out.error.__cause__, PlaywrightTimeoutError)
            assert "Timeout 80ms exceeded" in str(timed_out.error)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("java_script_enabled", "expected_marker"),
    ((True, "executed"), (False, "not-executed")),
)
async def test_chromium_honors_context_java_script_policy(
    java_script_enabled: bool,
    expected_marker: str,
) -> None:
    async with BrowserSession(
        options=BrowserOptions(headless=True, timeout=10_000),
        context_options=BrowserContextOptions(java_script_enabled=java_script_enabled),
    ) as session:
        page = session.page
        document = quote(
            "<body data-marker='not-executed'>"
            "<script>document.body.dataset.marker='executed'</script>"
            "</body>"
        )
        navigated = await page.navigate(f"data:text/html,{document}")
        assert navigated.is_ok(), navigated
        marker = await page.evaluate("() => document.body.dataset.marker")
        assert marker.is_ok(), marker
        assert marker.ok == expected_marker


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_honors_context_https_error_policy() -> None:
    async with local_response_server(
        body=b"<title>trusted by policy</title>",
        ssl_context=self_signed_server_context(),
    ) as server:
        async with BrowserSession(
            options=BrowserOptions(headless=True, timeout=10_000)
        ) as session:
            browser = session.environment.require(BROWSER)
            strict_outcome = await browser.new_context(
                BrowserContextOptions(ignore_https_errors=False)
            )
            assert strict_outcome.is_ok(), strict_outcome
            strict_context = strict_outcome.ok
            try:
                strict_page_outcome = await strict_context.new_page()
                assert strict_page_outcome.is_ok(), strict_page_outcome
                rejected = await strict_page_outcome.ok.navigate(server.url)
                assert rejected.is_error(), rejected
                assert "ERR_CERT_AUTHORITY_INVALID" in str(rejected.error)
            finally:
                closed = await strict_context.close()
                assert closed.is_ok(), closed

            permissive_outcome = await browser.new_context(
                BrowserContextOptions(ignore_https_errors=True)
            )
            assert permissive_outcome.is_ok(), permissive_outcome
            permissive_context = permissive_outcome.ok
            try:
                permissive_page_outcome = await permissive_context.new_page()
                assert permissive_page_outcome.is_ok(), permissive_page_outcome
                accepted = await permissive_page_outcome.ok.navigate(server.url)
                assert accepted.is_ok(), accepted
                title = await permissive_page_outcome.ok.title()
                assert title.is_ok(), title
                assert title.ok == "trusted by policy"
            finally:
                closed = await permissive_context.close()
                assert closed.is_ok(), closed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_routes_a_context_through_its_authenticated_proxy() -> None:
    body = b"<title>proxied by Silk</title><main>proxy reached</main>"
    expected_authorization = b"basic c2lsazpzZWNyZXQ="
    async with local_response_server(
        body=body,
        required_proxy_authorization=expected_authorization,
    ) as proxy:
        async with BrowserSession(
            options=BrowserOptions(headless=True, timeout=10_000),
            context_options=BrowserContextOptions(
                proxy=BrowserProxy(
                    server=proxy.url.rsplit("/", 1)[0],
                    username="silk",
                    password="secret",
                )
            ),
        ) as session:
            page = session.page
            navigated = await page.navigate(
                "http://silk-proxy-target.invalid/context-proxy"
            )
            assert navigated.is_ok(), navigated
            assert any(
                request.startswith(
                    b"GET http://silk-proxy-target.invalid/context-proxy"
                )
                for request in proxy.requests
            )
            title = await page.title()
            assert title.is_ok(), title
            await asyncio.wait_for(
                proxy.proxy_authorization_seen.wait(),
                timeout=2,
            )
            assert any(
                (b"proxy-authorization: " + expected_authorization).lower()
                in request.lower()
                for request in proxy.requests
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chromium_bypasses_a_context_proxy_for_configured_hosts() -> None:
    body = b"<title>direct target</title><main>proxy bypassed</main>"
    async with (
        local_response_server(body=body) as target,
        local_response_server(body=b"unexpected proxy") as proxy,
    ):
        async with BrowserSession(
            options=BrowserOptions(
                headless=True,
                timeout=10_000,
                args=("--host-resolver-rules=MAP silk-bypass.test 127.0.0.1",),
            ),
            context_options=BrowserContextOptions(
                proxy=BrowserProxy(
                    server=proxy.url.rsplit("/", 1)[0],
                    bypass="silk-bypass.test",
                )
            ),
        ) as session:
            page = session.page
            target_url = target.url.replace(
                "127.0.0.1",
                "silk-bypass.test",
            )
            navigated = await page.navigate(target_url)
            assert navigated.is_ok(), navigated
            title = await page.title()
            assert title.is_ok(), title
            assert title.ok == "direct target"
            assert target.requests
            assert proxy.requests == []
