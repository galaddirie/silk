# Changelog

## [0.3.1] - 2025-06-08

### Added
- Add `parent` argument to `Query`, `QueryAll`, `GetText`, `GetInnerText`, and `GetHtml` actions.

### Changed
- bump fp-ops to 0.2.11

## [0.3.0] - 2025-05-26

### Added
- New `silk.actions.browser` module for enhanced context and page management operations like `CreateContext`, `CreatePage`, `SwitchToPage`, `CloseCurrentPage`, `CloseContext`, `WithNewTab`, `GetAllPages`, `FocusPage`, `ReloadPage`, `GetCurrentUrl`, `GetPageTitle`, and `WithMetadata`.
- `BrowserSession` class in `silk.browsers.sessions` for simplified browser lifecycle management.
- `Driver`, `BrowserContext`, `Page`, and `ElementHandle` protocols in `silk.browsers.models` are now the source of truth for browser object interactions, promoting a more decoupled architecture.
- `PlaywrightDriver` now manages Playwright object references (contexts, pages, elements) internally using IDs, reducing direct exposure of Playwright primitives.
- `PlaywrightElementHandle`, `PlaywrightPage`, and `PlaywrightBrowserContext` are lightweight wrappers delegating calls to the `PlaywrightDriver`.
- Added `__all__` to `silk.composition`, `silk.operation`, and `silk.placeholder` for better public API definition.

### Changed
- **Breaking Change**: `silk.actions.context.ActionContext` has been removed. The `ActionContext` is now defined in `silk.browsers.models.ActionContext`. This new `ActionContext` directly holds `Driver`, `BrowserContext`, and `Page` protocol instances instead of IDs and a `BrowserManager`.
- **Breaking Change**: `silk.actions.manage` module has been removed. Its functionalities are replaced or integrated into the new `silk.actions.browser` module and `BrowserSession`.
- **Breaking Change**: Actions in `silk.actions.elements`, `silk.actions.input`, and `silk.actions.navigation` now expect an `ActionContext` (from `silk.browsers.models`) that provides direct `driver`, `context`, and `page` attributes.
- **Breaking Change**: `silk.browsers.driver_factory` has been removed. Driver instantiation is expected to be handled by `BrowserSession` or manually.
- `PlaywrightDriver` launch and object creation methods now return `Result` objects for consistent error handling.
- Simplified `PlaywrightElementHandle` to primarily hold IDs and delegate operations to the `PlaywrightDriver`.
- Updated `silk.actions.elements.ElementExists` to use the `selector` argument explicitly.

### Fixed
- Potential issues with context and page lifecycles by centralizing their management within `PlaywrightDriver` and `BrowserSession`.
- Improved clarity of public API.


## [0.2.5] - 2025-04-15

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
