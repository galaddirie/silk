#!/usr/bin/env python
"""
Update version number in all relevant files.

Usage:
    python scripts/update_version.py 0.1.1
"""

import re
import sys
from pathlib import Path


def update_version(new_version: str) -> None:
    """Update version in all relevant files."""

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", new_version):
        print(f"Error: Invalid version format '{new_version}', should be X.Y.Z")
        sys.exit(1)

    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        updated = re.sub(
            r'(^\[project\].*?version = ")[^"]+(.*?)$',
            rf"\1{new_version}\2",
            content,
            flags=re.DOTALL | re.MULTILINE,
        )
        pyproject_path.write_text(updated)
        print(f"Updated version in {pyproject_path} to {new_version}")

    # Update __init__.py
    init_path = Path("src/silk/__init__.py")
    if init_path.exists():
        content = init_path.read_text()
        updated = re.sub(
            r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content
        )
        init_path.write_text(updated)
        print(f"Updated version in {init_path} to {new_version}")

    # Update README badge
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text()
        updated = re.sub(
            r"pypi-v\d+\.\d+\.\d+-blue", f"pypi-v{new_version}-blue", content
        )
        readme_path.write_text(updated)
        print(f"Updated version in {readme_path} to {new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/update_version.py VERSION")
        sys.exit(1)

    update_version(sys.argv[1])
    print(f"Version updated to {sys.argv[1]}")
