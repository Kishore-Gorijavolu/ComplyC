# Known Issues

This document lists known limitations of the current **ComplyC v0.9.0-beta Community Edition**.

These limitations do not prevent normal use of ComplyC, but users should consider them when interpreting analysis results.

## Preprocessing and Compiler Extensions

ComplyC uses GCC-compatible preprocessing before AST-based analysis.

Embedded projects may contain compiler-specific extensions, proprietary pragmas, vendor headers, conditional compilation, or build-system definitions that GCC cannot process directly.

ComplyC includes preprocessing recovery and compiler-extension sanitization to improve compatibility. However, some projects may still require additional include paths, macro definitions, or preprocessing configuration.

If preprocessing cannot be fully recovered, affected files may be skipped or reported in the scan-error report.

## Source Mapping

ComplyC includes source indexing and source-mapping support to map analysis findings back to the original source files and line numbers.

Source attribution is expected to be accurate for normal C source analysis. However, complex macro expansion, generated code, deeply nested includes, or unusual preprocessing constructs may occasionally result in imperfect source attribution.

Users should verify the referenced source location when reviewing findings involving complex preprocessing.

## Header Attribution

ComplyC attempts to distinguish findings originating from the selected source file from declarations introduced through included headers.

Complex preprocessing or compiler-generated constructs may occasionally make header/source attribution ambiguous.

Additional header filtering and source-attribution improvements may be introduced based on community feedback.

## Experimental Dataflow Analysis

Advanced dataflow rules are not enabled in the current Community Beta.

The following analysis capabilities remain experimental or planned:

* Uninitialized variable detection
* Dead-store detection
* Unused-variable detection
* Advanced interprocedural dataflow analysis

These rules will be enabled only after their control-flow and dataflow behavior has been sufficiently validated to avoid excessive false positives.

## Security Analysis

The Community Beta includes a limited set of security-oriented and defensive coding checks, including unsafe library API usage, dynamic memory usage, and recursion detection.

ComplyC v0.9.0-beta is **not intended to provide complete cybersecurity, CERT C, CWE, or vulnerability analysis**.

A broader Security Rule Pack with dedicated security rule IDs and CWE mappings is planned for a future release.

## Rule Coverage

Some rules present in the example or development rule configuration may be intentionally disabled when their analysis handlers are experimental or not yet available.

Disabled rules are not evaluated during a scan and should not be interpreted as supported checks.

Rule coverage will continue to expand in future releases.

## Beta Status

ComplyC v0.9.0-beta is a Community Beta intended for evaluation, testing, and feedback on real-world Embedded C projects.

Users may encounter project-specific preprocessing constructs, compiler extensions, or coding patterns that have not yet been tested.

Please report reproducible issues with:

* ComplyC version
* Compiler/toolchain
* Minimal source-code example
* Rule ID, if applicable
* Expected behavior
* Actual behavior

## Current Development Priorities

1. Embedded project and compiler compatibility
2. Analysis accuracy and false-positive reduction
3. Control-flow and dataflow analysis improvements
4. Expanded coding-standard and security rule coverage
5. Community-reported bug fixes and usability improvements
