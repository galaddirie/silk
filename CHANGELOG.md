# Changelog
## [0.2.4] - 2025-04-15

### Fixed
- patch fill and type
- support patchwright driver
- fix scroll
- add proper scroll method to BrowserDriver protocol and implement in PlaywrightDriver
- add SelectorGroup iterator, len, getitem, contains, repr, str
- QueryAll now returns empty list instead of throwing an error
- Query now returns None instead of throwing an error
- ElementExists now returns False instead of throwing an error
- GetAttribute now returns None instead of throwing an error
- GetText now returns empty string instead of throwing an error
- GetInnerText now returns empty string instead of throwing an error
- GetHtml now returns empty string instead of throwing an error

## [0.2.3] - 2025-04-14

### Fixed
- fix release
- removed old actions.composition.py


## [0.2.2] - 2025-04-14

### Fixed
- fix release

## [0.2.1] - 2025-04-14

### Fixed
- fix import error with expression library

## [0.2.0] - 2025-04-13

### Added
- Complete API reference documentation
- Enhanced context management with `InitializeContext` and `WithContext`
- New selector system with improved fallback mechanisms
- Map operations for collections with `.map()` method
- Improved type hints throughout the codebase

### Changed
- Complete refactor using [fp-ops](https://github.com/galaddirie/fp-ops/)
- Module restructuring:
  - Moved extraction actions from `silk.actions.extraction` to `silk.actions.elements`
  - Moved flow control functions from `silk.actions.flow` to `silk.flow`
  - Moved composition functions from `silk.actions.composition` to `silk.composition` 
  - Moved browser options from `silk.models.browser` to `silk.browsers.types`
- Changed execution model to explicitly use contexts: `action(context)` instead of `action(manager)`
- Improved error handling with more detailed error types
- Enhanced retry mechanisms with better backoff strategies
- Optimized parallel execution for better performance

### Fixed
- Fixed context propagation issues in nested actions
- Resolved race conditions in parallel execution
- Improved error reporting with more descriptive messages
- Fixed selector resolution in complex DOM structures

### Breaking Changes
- All actions now require a context parameter instead of a manager
- Changed import paths for many core components
- Renamed several functions for consistency
- Modified function signatures to support the new context-based model


## [0.1.6] - 2025-04-08

### Added

### Fixed
- desync between pypi and github releases skipping 0.1.5

### Changed



## [0.1.4] - 2025-04-08

### Added

### Fixed
- readme updates

### Changed


## [0.1.3] - 2025-04-08

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
