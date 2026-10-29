"""Standalone installed-wheel smoke; execute this file outside the checkout."""

from __future__ import annotations

import asyncio
import os
import re
from importlib import import_module, metadata, util
from inspect import signature
from pathlib import Path
from types import ModuleType
from typing import Protocol, runtime_checkable

from fp_ops import Operation, _, __version__ as fp_ops_version

import silk
from silk.actions.elements import GetInnerText
from silk.actions.navigation import Navigate
from silk.browsers.models import BROWSER, BrowserOptions, Page
from silk.browsers.sessions import BrowserSession

BOOKS_URL = "https://books.toscrape.com/"
EXPECTED_DISTRIBUTION_NAME = "silk-scraper"
EXPECTED_SILK_VERSION = "0.4.1"
EXPECTED_DIRECT_REQUIREMENTS = {
    "fp-ops>=0.5.0,<0.6.0",
    "playwright>=1.61.0,<2.0.0",
    "typing-extensions>=4.12.0,<5.0.0",
}
FORBIDDEN_DIRECT_REQUIREMENTS = (
    "expression",
    "patchright",
    "pydantic",
    "pydantic-settings",
)
PACKAGE_INITIALIZERS = (
    "silk",
    "silk.actions",
    "silk.browsers",
    "silk.browsers.drivers",
    "silk.selectors",
)
DELETED_MODULES = (
    "silk.composition",
    "silk.flow",
    "silk.objects",
    "silk.operation",
    "silk.placeholder",
    "silk.text",
    "silk.utils",
    "silk.actions.utils",
    "silk.browsers.capabilities",
)


@runtime_checkable
class PublicPackageInitializer(Protocol):
    """Runtime-checkable shape of an initializer with explicit exports."""

    __all__: list[str]


def normalized_requirement(requirement: str) -> str:
    """Normalize insignificant metadata whitespace and parentheses."""

    return re.sub(r"[\s()]", "", requirement).lower()


def verify_public_exports(module: ModuleType) -> None:
    """Require each package initializer to bind every advertised name."""

    module_name = module.__name__
    assert isinstance(module, PublicPackageInitializer), module_name
    advertised_names = module.__all__
    assert isinstance(advertised_names, list), module_name
    for name in advertised_names:
        assert isinstance(name, str) and name, (module_name, name)
        assert hasattr(module, name), (module_name, name)
    assert len(advertised_names) == len(set(advertised_names)), module_name


def verify_distribution() -> None:
    distribution = metadata.distribution(EXPECTED_DISTRIBUTION_NAME)
    assert distribution.metadata["Name"] == EXPECTED_DISTRIBUTION_NAME
    distribution_version = distribution.version
    assert distribution_version == EXPECTED_SILK_VERSION
    assert silk.__version__ == EXPECTED_SILK_VERSION
    assert distribution_version == silk.__version__

    assert fp_ops_version == "0.5.0"
    requirements = metadata.requires(EXPECTED_DISTRIBUTION_NAME) or []
    # Extras (``; extra == "static"``) are optional, not direct requirements.
    direct = [item for item in requirements if "extra ==" not in item]
    normalized = {normalized_requirement(item) for item in direct}
    assert normalized == EXPECTED_DIRECT_REQUIREMENTS, requirements
    for forbidden in FORBIDDEN_DIRECT_REQUIREMENTS:
        assert not any(
            requirement == forbidden
            or requirement.startswith(forbidden + "<")
            or requirement.startswith(forbidden + ">")
            or requirement.startswith(forbidden + "=")
            for requirement in normalized
        ), requirements
    assert sorted(distribution.metadata.get_all("Provides-Extra") or []) == [
        "httpx",
        "static",
    ], distribution.metadata.get_all("Provides-Extra")

    imported = Path(silk.__file__).resolve()
    assert any(
        part in {"site-packages", "dist-packages"} for part in imported.parts
    ), imported
    assert (imported.parent / "py.typed").is_file(), imported.parent

    checkout_value = os.environ.get("SILK_CHECKOUT")
    if checkout_value is not None:
        checkout = Path(checkout_value).resolve()
        assert checkout not in imported.parents, imported
        assert Path.cwd().resolve() != checkout

    for package_name in PACKAGE_INITIALIZERS:
        verify_public_exports(import_module(package_name))

    browser_package = import_module("silk.browsers")
    browser_models = import_module("silk.browsers.models")
    driver_package = import_module("silk.browsers.drivers")
    playwright_adapter = import_module("silk.browsers.drivers.playwright")
    session_module = import_module("silk.browsers.sessions")
    for module in (
        silk,
        browser_package,
        browser_models,
        driver_package,
        playwright_adapter,
        session_module,
    ):
        assert not hasattr(module, "Driver"), module.__name__
    assert driver_package.__all__ == [
        "PlaywrightDriver",
        "attempt",
        "attempt_blocking",
    ]
    assert driver_package.PlaywrightDriver is playwright_adapter.PlaywrightDriver
    assert issubclass(driver_package.PlaywrightDriver, browser_models.BrowserDriver)
    assert issubclass(
        playwright_adapter.PlaywrightBrowser, browser_models.LaunchedBrowser
    )

    session_parameters = signature(BrowserSession).parameters
    assert tuple(session_parameters) == ("options", "context_options", "driver")
    assert "driver_class" not in session_parameters
    assert "driver_factory" not in session_parameters

    session = BrowserSession()
    assert not hasattr(BrowserSession, "_for_testing")
    for forbidden_access in (
        "driver",
        "driver_factory",
        "_driver_factory",
        "_resources",
    ):
        assert not hasattr(session, forbidden_access), forbidden_access

    for module_name in DELETED_MODULES:
        try:
            found = util.find_spec(module_name)
        except ModuleNotFoundError:
            found = None
        assert found is None, module_name


async def verify_public_browser_pipeline() -> None:
    pipeline: Operation[Page, str] = Navigate(_, BOOKS_URL).then(GetInnerText("h1", _))
    assert isinstance(pipeline, Operation)

    async with BrowserSession(
        options=BrowserOptions(headless=True),
    ) as session:
        browser = session.environment.require(BROWSER)
        result = await pipeline.run(
            session.page,
            environment=session.environment,
        )

    assert result.is_ok(), result
    assert result.ok.strip() == "All products"
    assert session.is_started is False
    stale = await browser.new_context()
    assert stale.is_error()


def main() -> None:
    verify_distribution()
    asyncio.run(verify_public_browser_pipeline())
    print("installed wheel smoke passed")


if __name__ == "__main__":
    main()
