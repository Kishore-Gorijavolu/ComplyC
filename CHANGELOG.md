
## v0.2.4 - Source Index Engine Stabilization

- Stabilized Source Index Engine as the authoritative original-source lookup layer.
- Replaced mutable numeric literal cursor with deterministic literal lookup.
- Added O(1)-style cached source indexing with bounded cache.
- Added local static declaration indexing regression coverage.
- Added source_callgraph.py compatibility wrapper around Source Index Engine.
- Added docs/SourceIndexEngine.md and tests/test_source_index_engine.py.
- Improved magic-number macro suppression using mapped original source lines.

# Changelog

All notable changes to **ComplyC** will be documented in this file.

## v0.2.1 - 2026-06-26

### Added

-   Project-aware GUI
-   Automatic project detection
-   GCC preprocessing support
-   Automatic include-path discovery
-   HTML/JSON reports
-   Error report generation
-   Windows executable packaging

### Improved

-   Embedded project discovery
-   Include folder detection
-   Scan workflow

### Known Limitations

-   Original source line mapping is not implemented.
-   Header-origin violations may be attributed to the selected source
    file.
-   Dataflow analysis is experimental.

## v0.2.5-dev - Compiler Extension Sanitizer integrated

- Added `complyc/compiler_extensions.py` as the current parser architecture layer for compiler-specific syntax normalization.
- Moved GCC-style `__attribute__((...))` handling out of ad-hoc parser cleanup and into a dedicated sanitizer.
- Added support for common embedded/compiler extension tokens such as `__weak`, `__irq`, `__packed`, `__root`, `__ramfunc`, `__inline__`, `__restrict__`, and basic pragma/inline assembly removal.
- Updated `parser.py` so both GCC and built-in parser modes pass code through the compiler extension sanitizer before pycparser.
- Added `tests/regression/compiler_extensions_fixture.c` to verify GCC attributes and common embedded extension markers parse successfully.
