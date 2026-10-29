"""Browser session lifecycle."""

# pyright: strict

from __future__ import annotations

from types import TracebackType
from typing import Self, TypeVar

from fp_ops import Environment, Result

from silk.browsers.drivers.playwright import PlaywrightDriver
from silk.browsers.models import (
    BROWSER,
    CONTEXT,
    Browser,
    BrowserContext,
    BrowserContextOptions,
    BrowserDriver,
    BrowserOptions,
    LaunchedBrowser,
    Page,
)

T = TypeVar("T")


class SessionBrowser(Browser):
    """The session's browser as pipelines see it: ``new_context()`` without
    options uses the session's ``context_options``, so contexts opened inside a
    pipeline match the session's first one."""

    def __init__(
        self,
        browser: Browser,
        defaults: BrowserContextOptions | None,
    ) -> None:
        self._browser = browser
        self._defaults = defaults

    @property
    def defaults(self) -> BrowserContextOptions | None:
        return self._defaults

    async def new_context(
        self,
        options: BrowserContextOptions | None = None,
    ) -> Result[BrowserContext, Exception]:
        return await self._browser.new_context(
            options if options is not None else self._defaults
        )


class BrowserSession:
    """Own one browser, its initial context, and its initial page.

    The page is ordinary pipeline input; the environment provides the
    :class:`Browser` under :data:`BROWSER` for actions such as
    ``CreateContext``::

        async with BrowserSession() as session:
            result = await pipeline.run(
                session.page,
                environment=session.environment,
            )

    Closing the session closes the browser, which closes every context and
    page opened in it.

    ``driver`` launches the browser; it defaults to Chromium through
    :class:`~silk.browsers.drivers.PlaywrightDriver`.
    """

    def __init__(
        self,
        options: BrowserOptions | None = None,
        *,
        context_options: BrowserContextOptions | None = None,
        driver: BrowserDriver | None = None,
    ) -> None:
        self._options = options if options is not None else BrowserOptions()
        self._context_options = context_options
        self._driver = driver if driver is not None else PlaywrightDriver()
        self._browser: LaunchedBrowser | None = None
        self._session_browser: SessionBrowser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def is_started(self) -> bool:
        return self._page is not None

    @property
    def browser(self) -> Browser:
        """The running browser; new contexts default to the session's options."""

        return self._require(self._session_browser)

    @property
    def context(self) -> BrowserContext:
        return self._require(self._context)

    @property
    def page(self) -> Page:
        return self._require(self._page)

    @property
    def environment(self) -> Environment:
        """``BROWSER``, ``CONTEXT`` (the session's first context) and ``HTTP``
        (its request API, sharing the context's cookies) for pipelines."""

        from silk.http import HTTP, ContextHttpClient

        return (
            Environment()
            .with_value(BROWSER, self.browser)
            .with_value(CONTEXT, self.context)
            .with_value(HTTP, ContextHttpClient(self.context))
        )

    async def start(self) -> Self:
        """Launch the browser and open the initial context and page."""

        if self._browser is not None:
            raise RuntimeError("browser session is already started")
        browser = await self._driver.launch(self._options)
        try:
            context = await browser.new_context(self._context_options)
            if context.is_error():
                raise context.error
            page = await context.ok.new_page()
            if page.is_error():
                raise page.error
        except BaseException:
            await browser.close()
            raise
        self._browser, self._context, self._page = browser, context.ok, page.ok
        self._session_browser = SessionBrowser(browser, self._context_options)
        return self

    async def close(self) -> None:
        """Close the browser. Safe to call more than once."""

        browser = self._browser
        self._browser = self._context = self._page = None
        self._session_browser = None
        if browser is not None:
            await browser.close()

    async def __aenter__(self) -> Self:
        return await self.start()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    @staticmethod
    def _require(value: T | None) -> T:
        if value is None:
            raise RuntimeError("browser session is not started")
        return value


__all__ = ["BrowserSession", "SessionBrowser"]
