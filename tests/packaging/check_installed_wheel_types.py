"""Type-check public consumer contracts against an installed wheel only."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKER_REQUIREMENTS = ("mypy==1.15.0", "pyright==1.1.411")
# The copied consumers include fixtures for the optional ``silk.http`` and
# ``silk.static`` modules, so install the wheel the way their users would.
WHEEL_EXTRAS = ("httpx", "static")
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
PYRIGHT_CONFIG = {
    "include": ["consumer"],
    "pythonVersion": PYTHON_VERSION,
    "typeCheckingMode": "strict",
}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse the one wheel artifact this isolated check must install."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "wheel",
        type=Path,
        help="path to the newly built silk wheel",
    )
    return parser.parse_args(argv)


def sanitized_environment() -> dict[str, str]:
    """Remove variables that can put the checkout on an import path."""

    environment = os.environ.copy()
    for variable in (
        "MYPYPATH",
        "PYTHONHOME",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    ):
        environment.pop(variable, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONSAFEPATH"] = "1"
    return environment


def consumer_contracts() -> tuple[Path, ...]:
    """Discover every standalone positive contract copied into the sandbox."""

    example = ROOT / "examples" / "books_to_scrape.py"
    good_fixtures = set((ROOT / "tests").rglob("*_good.py"))
    browser_seams = set((ROOT / "tests" / "browsers").rglob("typecheck_*.py"))
    contracts = tuple(sorted({example, *good_fixtures, *browser_seams}))

    assert example.is_file(), example
    assert good_fixtures, "no *_good.py consumer fixtures were discovered"
    assert browser_seams, "no browser seam consumer fixtures were discovered"
    assert all(path.is_file() for path in contracts), contracts
    return contracts


def verify_wheel_marker(wheel: Path) -> None:
    """Require the PEP 561 marker in the artifact, not merely the checkout."""

    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
    assert "silk/py.typed" in members, f"{wheel.name} does not contain silk/py.typed"


def copy_contracts(sandbox: Path) -> tuple[Path, ...]:
    """Copy contracts without making the checkout importable from their cwd."""

    consumer_root = sandbox / "consumer"
    copied: list[Path] = []
    for source in consumer_contracts():
        destination = consumer_root / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    return tuple(copied)


def run_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> None:
    """Run a gate command and show its exact isolated invocation."""

    print("+", " ".join(command), flush=True)
    subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=True,
    )


def verify_import_origin(
    python: Path,
    *,
    sandbox: Path,
    environment: dict[str, str],
) -> None:
    """Prove the checker interpreter imports Silk from site-packages."""

    code = """
import pathlib
import silk
import sys

checkout = pathlib.Path(sys.argv[1]).resolve()
origin = pathlib.Path(silk.__file__).resolve()
assert checkout not in origin.parents, origin
assert any(part in {"site-packages", "dist-packages"} for part in origin.parts), origin
print(f"installed silk import: {origin}")
"""
    run_checked(
        (str(python), "-I", "-c", code, str(ROOT)),
        cwd=sandbox,
        environment=environment,
    )


def check_installed_wheel(wheel: Path) -> None:
    """Install and type-check copied contracts in a fresh external sandbox."""

    resolved_wheel = wheel.resolve(strict=True)
    assert resolved_wheel.suffix == ".whl", resolved_wheel
    verify_wheel_marker(resolved_wheel)

    environment = sanitized_environment()
    with tempfile.TemporaryDirectory(prefix="silk-wheel-types-") as directory:
        sandbox = Path(directory).resolve()
        assert ROOT != sandbox and ROOT not in sandbox.parents, sandbox
        assert sandbox not in ROOT.parents, sandbox

        copied = copy_contracts(sandbox)
        virtualenv = sandbox / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(virtualenv)
        executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        python = virtualenv / executable

        run_checked(
            (
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                f"silk-scraper[{','.join(WHEEL_EXTRAS)}] @ {resolved_wheel.as_uri()}",
                *CHECKER_REQUIREMENTS,
            ),
            cwd=sandbox,
            environment=environment,
        )
        verify_import_origin(
            python,
            sandbox=sandbox,
            environment=environment,
        )

        relative_contracts = tuple(str(path.relative_to(sandbox)) for path in copied)
        mypy_config = sandbox / "mypy.ini"
        mypy_config.write_text("[mypy]\n", encoding="utf-8")
        run_checked(
            (
                str(python),
                "-I",
                "-m",
                "mypy",
                "--config-file",
                str(mypy_config),
                "--strict",
                "--python-executable",
                str(python),
                "--python-version",
                PYTHON_VERSION,
                *relative_contracts,
            ),
            cwd=sandbox,
            environment=environment,
        )

        config = sandbox / "pyrightconfig.json"
        config.write_text(
            json.dumps(PYRIGHT_CONFIG, indent=2) + "\n",
            encoding="utf-8",
        )
        run_checked(
            (
                str(python),
                "-I",
                "-m",
                "pyright",
                "--project",
                str(config),
                "--pythonpath",
                str(python),
                "--pythonversion",
                PYTHON_VERSION,
            ),
            cwd=sandbox,
            environment=environment,
        )

        print(
            f"installed-wheel static contracts passed: {len(copied)} files",
            flush=True,
        )


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""

    arguments = parse_args(argv)
    check_installed_wheel(arguments.wheel)


if __name__ == "__main__":
    main()
