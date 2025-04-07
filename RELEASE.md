# Release Process for Silk

This document outlines the steps to release a new version of the Silk package to PyPI.

## Automated Release Process

Silk uses an automated release process that builds on PR-based changelog generation:

1. **Every merged PR to main automatically updates the changelog** if it contains a changelog entry in the PR template.
2. **Releases are initiated via GitHub Actions** using the "Create Release" workflow.

## PR-Based Changelog Generation

1. When opening a PR to main, fill out the PR template, including:
   - Check the appropriate "Type of Change" box(es)
   - Add a clear changelog entry in the "Changelog Entry" section

2. After your PR is approved and merged, the changelog will be automatically updated based on your PR.

## Creating a Release

### Option 1: Automated Release (Recommended)

1. Go to the GitHub Actions tab in the repository
2. Select the "Create Release" workflow
3. Click "Run workflow"
4. Fill in the required information:
   - **Version**: (leave empty to auto-increment based on the type)
   - **Type**: Choose `patch`, `minor`, or `major`
5. Click "Run workflow"

The workflow will:
- Update version numbers in all relevant files
- Update CHANGELOG.md with the release date
- Create a draft GitHub release
- When you publish the GitHub release, it will trigger the PyPI publishing workflow

### Option 2: Manual Release (Fallback)

If the automation fails for any reason, you can follow these steps:

1. **Update Version**

   ```bash
   python scripts/update_version.py X.Y.Z
   ```

2. **Update CHANGELOG.md**

   - Update the release date
   - Add any missing entries

3. **Create and push release commit**

   ```bash
   git add .
   git commit -m "Release vX.Y.Z"
   git push origin main
   ```

4. **Create Release Tag**

   Create a new release on GitHub manually:
   
   - Tag format: `vX.Y.Z`
   - Title: `Version X.Y.Z`
   - Description: Copy relevant section from CHANGELOG.md

5. **Wait for CI/CD**

   The GitHub workflow will automatically:
   
   - Run tests
   - Build the package
   - Upload to PyPI

## Post-Release

1. [ ] Verify the package is available on PyPI: https://pypi.org/project/silk-scraper/
2. [ ] Test installation: `pip install silk-scraper=={new_version}`
3. [ ] Announce the release on appropriate channels
4. [ ] Close any related issues and milestones 