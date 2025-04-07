#!/usr/bin/env python
"""
Extract changelog entries for a specific version.

This script extracts the changelog entries for a specific version from CHANGELOG.md,
which can be used in GitHub releases.

Usage:
    python scripts/extract_changelog.py [version]

If version is not specified, it extracts entries for the latest version.
"""

import re
import sys
from pathlib import Path


def extract_changelog(version=None):
    """Extract changelog entries for a specific version."""
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("Error: CHANGELOG.md not found")
        return None

    content = changelog_path.read_text()

    # If no version specified, get the latest version
    if not version:
        match = re.search(r'## \[([0-9]+\.[0-9]+\.[0-9]+)\]', content)
        if not match:
            print("Error: No version found in CHANGELOG.md")
            return None
        version = match.group(1)
        print(f"Extracting changelog for latest version: {version}")

    # Extract the changelog for the specified version
    pattern = rf'## \[{version}\][^\n]*\n(.*?)(?=\n## \[|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print(f"Error: Version {version} not found in CHANGELOG.md")
        return None
    
    changelog = match.group(1).strip()
    return changelog


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else None
    changelog = extract_changelog(version)
    
    if changelog:
        print(changelog)
    else:
        sys.exit(1) 