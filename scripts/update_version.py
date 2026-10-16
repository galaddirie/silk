#!/usr/bin/env python
"""Update every checked-in package-version contract.

Usage:
    python scripts/update_version.py 0.1.1
"""

import re
import sys
from pathlib import Path

VERSION_FILES = (
    (Path("pyproject.toml"), r'(?m)^(version = ")[^"]+("\s*)$'),
    (
        Path("src/silk/__init__.py"),
        r'(?m)^(__version__ = ")[^"]+("\s*)$',
    ),
    (
        Path("tests/packaging/installed_wheel_smoke.py"),
        r'(?m)^(EXPECTED_SILK_VERSION = ")[^"]+("\s*)$',
    ),
)


def _replace_exactly_once(path: Path, pattern: str, version: str) -> None:
    """Replace one version contract, failing if the expected seam drifts."""

    content = path.read_text(encoding="utf-8")
    updated, replacements = re.subn(
        pattern,
        lambda match: f"{match.group(1)}{version}{match.group(2)}",
        content,
    )
    if replacements != 1:
        raise RuntimeError(
            f"expected exactly one version contract in {path}, " f"found {replacements}"
        )
    path.write_text(updated, encoding="utf-8")
    print(f"Updated version in {path} to {version}")


def update_version(new_version: str) -> None:
    """Update package metadata, runtime, and installed-wheel expectations."""

    if re.fullmatch(r"\d+\.\d+\.\d+", new_version) is None:
        raise ValueError(f"invalid version {new_version!r}; expected X.Y.Z")

    for path, pattern in VERSION_FILES:
        _replace_exactly_once(path, pattern, new_version)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/update_version.py VERSION")

    update_version(sys.argv[1])
    print(f"Version updated to {sys.argv[1]}")
