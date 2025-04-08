# Changelog

## [0.1.3]

### Added

### Fixed

- fix incorrect pypi links

### Changed




All notable changes to this project will be documented in this file.


## [0.1.2] - 2025-04-08

### Added

### Fixed
- housekeeping, fixing imports, updating readme

### Changed


## [0.1.1] - 2025-04-08

### Added
- Add support for creating selector groups with unpacked selectors using `SelectorGroup(name, *selectors)`
- added tests for selectors and selector groups

### Fixed
- correct playwright driver import
- remove selenium and puppeteer drivers

### Changed
- removed SelectorGroup.create() and SelectorGroup.create_mixed() with constructor SelectorGroup(name, *selectors)

## [0.1.0] - 2025-04-08

### Added
Initial release of Silk
Support for Playwright browser automation
Functional API with Railway-Oriented Programming
Core action classes for navigation, extraction, and input
Composition operators for building scraping pipelines
Browser manager for handling browser sessions
Type safety with Pydantic models