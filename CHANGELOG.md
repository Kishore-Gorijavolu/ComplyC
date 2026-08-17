# Changelog

All notable changes to **ComplyC** are documented in this file.

ComplyC is an open-source static analysis and coding-guideline compliance tool focused on **Embedded C** and safety-critical software development.

---

## v0.9.0-beta - 2026-08-17

### Community Beta Release

First public Community Beta of ComplyC.

This release consolidates the rule engine, embedded-project preprocessing, source mapping, reporting, and desktop GUI into a community-testable package.

### Added

* Project-aware desktop GUI.
* Configurable YAML-based rule engine.
* Embedded C project scanning.
* Automatic project and source-file discovery.
* GCC preprocessing support.
* Automatic include-path discovery.
* Compiler Extension Sanitizer.
* Multi-phase preprocessing recovery.
* Source Index Engine.
* Original-source mapping.
* Header filtering and source attribution.
* Rule and violation filtering in the GUI.
* Source navigation from reported violations.
* HTML, JSON, and CSV reporting.
* Rule Summary visualization.
* Limited Security Summary reporting.
* Scan-error reporting.
* Windows executable packaging.

### Coding and Quality Checks

Community Beta includes checks covering areas such as:

* Function naming
* Global variable naming
* Static variable naming
* Macro naming
* Local variable naming
* File headers
* Function length
* Function parameter count
* Cyclomatic complexity
* Nesting depth
* Brace formatting
* Assignment inside conditions
* Required `default` in `switch`
* Empty statements
* Empty blocks
* Unreachable code
* Implicit switch fallthrough
* Infinite-loop constructs
* Forbidden `goto`
* Empty functions
* Control-flow structure
* Unsafe or forbidden APIs
* Dynamic memory usage
* Recursion

### Security-Oriented Checks

The Community Beta includes a limited set of defensive coding and security-oriented checks for:

* Unsafe C library APIs
* Dynamic memory usage
* Recursion

These checks are intended to identify high-confidence coding risks.

ComplyC v0.9.0-beta does not claim complete CERT C, CWE, Secure-C, MISRA, AUTOSAR, or cybersecurity compliance.

### Improved

* Embedded project compatibility.
* TI/vendor-header preprocessing.
* GCC preprocessing recovery.
* Source file and line-number reporting.
* Original-source attribution.
* Macro detection and naming validation.
* Report accuracy.
* Parser recovery for unsupported compiler constructs.
* GUI scan workflow.
* Violation presentation and filtering.
* HTML report presentation.
* Security-oriented report classification.

### Deferred

The following capabilities remain disabled or experimental pending additional validation:

* Magic-number enforcement
* Uninitialized-variable analysis
* Dead-store analysis
* Unused-variable analysis
* Advanced dataflow analysis
* Full Security Rule Pack
* Extended coding-standard rule packs

### Known Limitations

See `KNOWN_ISSUES.md` for current beta limitations and expected behavior.

---

## v0.2.5 - Compiler Extension and Preprocessing Reliability

### Added

* `compiler_extensions.py` as the parser architecture layer for compiler-specific syntax normalization.
* Support for common embedded/compiler extension tokens including:

  * `__weak`
  * `__irq`
  * `__packed`
  * `__root`
  * `__ramfunc`
  * `__inline__`
  * `__restrict__`
* Basic handling of compiler pragmas and inline assembly constructs.
* Regression fixture coverage for compiler-extension parsing.
* Additional preprocessing recovery for embedded projects.

### Improved

* Moved GCC-style `__attribute__((...))` handling into the dedicated Compiler Extension Sanitizer.
* Both GCC and built-in parser paths now use compiler-extension sanitization before `pycparser`.
* Improved recovery from unsupported compiler-specific constructs.
* Improved compatibility with TI/vendor header structures.
* Reduced unnecessary file skipping during preprocessing failures.

---

## v0.2.4 - Source Index Engine Stabilization

### Added

* Source Index Engine as the authoritative original-source lookup layer.
* Cached source indexing with bounded cache.
* Local static declaration indexing regression coverage.
* `source_callgraph.py` compatibility wrapper.
* `docs/SourceIndexEngine.md`.
* `tests/test_source_index_engine.py`.

### Improved

* Replaced mutable numeric-literal cursor logic with deterministic literal lookup.
* Improved original-source lookup performance.
* Improved source attribution consistency.
* Improved magic-number macro suppression using mapped original source lines.
* Improved source file and line-number resolution.

---

## v0.2.3 - Rule Engine and Analysis Expansion

### Added

* Additional configurable rule handlers.
* Function complexity analysis.
* Function nesting-depth checks.
* Function parameter-count checks.
* Empty-statement detection.
* Empty-block detection.
* Unreachable-code detection.
* Switch default validation.
* Implicit fallthrough detection.
* Assignment-in-condition detection.
* Forbidden-keyword support.
* Unsafe/forbidden function detection.
* Dynamic-memory checks.
* Recursion detection.

### Improved

* YAML-driven rule configuration.
* Rule scope dispatch.
* AST-based violation detection.
* Rule severity handling.
* Violation metadata generation.

---

## v0.2.2 - Reporting and GUI Improvements

### Added

* Rule-based GUI filtering.
* Violation filtering.
* Source navigation from violations.
* Rule Summary visualization.
* Limited Security Summary visualization.
* Additional report metadata.

### Improved

* HTML report layout.
* Violation presentation.
* Scan-result organization.
* Error reporting.
* GUI project workflow.
* Report consistency between analysis results and generated output.

---

## v0.2.1 - 2026-06-26

### Project-Aware Analysis Release

### Added

* Project-aware GUI.
* Automatic project detection.
* GCC preprocessing support.
* Automatic include-path discovery.
* HTML and JSON reports.
* Error-report generation.
* Windows executable packaging.

### Improved

* Embedded project discovery.
* Include-folder detection.
* Scan workflow.
* Project-level analysis.

### Known Limitations at Release

At the time of this release:

* Original-source mapping was not yet fully implemented.
* Header-origin violations could be attributed to the selected source file.
* Dataflow analysis was experimental.

These areas were subsequently improved in later releases.

---

## v0.2.0 - Core Analysis Architecture

### Added

* AST-based C source analysis using `pycparser`.
* Initial configurable rule-engine architecture.
* YAML coding-guideline configuration.
* Rule severity classification.
* Violation collection.
* File and function-level analysis.
* Initial control-flow analysis.
* Initial dataflow-analysis framework.

### Architecture

Established the primary ComplyC analysis pipeline:

```text
C Project
   |
   v
Project Discovery
   |
   v
Preprocessing
   |
   v
C Parser / AST
   |
   v
Rule Engine
   |
   v
Violation Collection
   |
   v
Reports
```

This release established the foundation for subsequent project-aware analysis, source mapping, reporting, and GUI development.

---

## v0.1.0 - Initial Prototype

### Added

* Initial ComplyC prototype.
* C source-file scanning.
* Basic coding-guideline checks.
* Initial rule configuration.
* Basic violation reporting.
* Early command-line analysis workflow.

### Purpose

The initial prototype established the core project goal:

> Analyze C source code against configurable coding guidelines and report actionable violations to developers.

---

# Version History

| Version         | Major Milestone                                |
| --------------- | ---------------------------------------------- |
| **v0.9.0-beta** | Community Beta                                 |
| **v0.2.5**      | Compiler Extension & Preprocessing Reliability |
| **v0.2.4**      | Source Index Engine Stabilization              |
| **v0.2.3**      | Rule Engine & Analysis Expansion               |
| **v0.2.2**      | Reporting & GUI Improvements                   |
| **v0.2.1**      | Project-Aware Analysis                         |
| **v0.2.0**      | Core Analysis Architecture                     |
| **v0.1.0**      | Initial Prototype                              |

---

## Release Status

**Current Release:** `v0.9.0-beta`

The Community Beta is intended for evaluation and feedback from Embedded C developers and software-quality engineers.

Future releases will focus on analysis accuracy, embedded-toolchain compatibility, additional coding-standard rules, security-oriented analysis, and validated control/dataflow capabilities.
