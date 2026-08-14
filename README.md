# ComplyC

### Configurable Coding-Guideline Compliance Analysis for Embedded C

**Current Release:** `v0.9.0-beta`
**Status:** Community Beta

ComplyC is an open-source, configurable static-analysis and coding-guideline compliance tool designed primarily for **embedded C projects**.

The project is intended to help engineering teams automate checks against organization-specific C coding guidelines using a YAML-based rule configuration instead of relying entirely on manual code reviews.

ComplyC combines source-level checks, C AST analysis, GCC preprocessing support, compiler-extension sanitization, source indexing, source mapping, and configurable rule evaluation to analyze embedded C source code and generate reviewable compliance reports.

> **Beta Notice:** ComplyC is currently under active development and is being released for community evaluation, testing, and technical feedback. It is not a certified MISRA, AUTOSAR, ISO 26262, or functional-safety qualification tool.

---

## Key Features

### Configurable YAML Rule Engine

Coding rules are defined in YAML rather than being permanently hard-coded into the application.

A rule can define information such as:

* Rule ID
* Rule title
* Analysis scope
* Check handler
* Severity
* Pattern or rule-specific configuration
* Guidance
* Coding-standard reference

Example:

```yaml
- id: NAMING_FUNC_001
  title: "Function names must be lower_snake_case"
  scope: function
  check: regex
  pattern: "^[a-z][a-z0-9_]*$"
  severity: major
  guidance: "Rename function to lower_snake_case."
  reference: "§3.2.1 Function Naming"
```

This architecture allows coding guidelines to evolve independently from the core application where supported rule handlers already exist.

---

## C Source Analysis

ComplyC uses **pycparser** to construct and analyze the C Abstract Syntax Tree (AST).

The analysis engine supports structural inspection of C source code including constructs such as:

* Functions
* Variables
* File-static variables
* Global variables
* Function calls
* Control-flow statements
* Loops
* Conditional statements
* Assignments
* Return statements
* Compound statements

AST-based checks are combined with source-level analysis where a rule cannot be reliably evaluated using the AST alone.

---

## Embedded-C Preprocessing

Real embedded projects frequently contain compiler-specific syntax, device headers, preprocessor conditions, attributes, and platform-specific declarations that generic C parsers cannot process directly.

ComplyC therefore includes a preprocessing and recovery pipeline intended to improve compatibility with real embedded projects.

### GCC Preprocessing

When configured for GCC preprocessing, ComplyC can use GCC to preprocess translation units before AST parsing.

The project supports:

* GCC preprocessing
* User-defined include directories
* Preprocessor defines
* Project include-path discovery
* Fake standard-library headers
* Preprocessing timeout protection
* Preprocessing failure handling

GCC must be installed and available on the system `PATH` when GCC preprocessing is selected.

### Built-in Preprocessing

A built-in preprocessing mode is also available for simpler source files or environments where GCC preprocessing is not required.

The built-in mode should not be considered equivalent to a real compiler preprocessor.

---

## Compiler Extension Sanitization

Embedded software often contains compiler-specific extensions that are not understood by a standard C parser.

ComplyC includes a compiler-extension sanitization layer to improve parser compatibility with these constructs before AST generation.

This is particularly useful when analyzing MCU/vendor-oriented embedded source code.

---

## Type Recovery

Preprocessed embedded code can still contain project-specific or vendor-specific types that prevent successful parsing.

ComplyC includes type-recovery support intended to identify and recover unresolved type information sufficiently for static analysis to continue where possible.

The objective is analyzer resilience rather than compilation or executable-code generation.

---

## Source Index Engine

ComplyC includes a Source Index Engine that independently indexes important source-code entities.

The index can identify source constructs such as:

* Function definitions
* Function declarations
* Function parameters
* Local variables
* File-static variables
* Global variables

The Source Index Engine complements AST analysis and helps improve source attribution and line-number recovery after preprocessing.

---

## Source Mapping

GCC preprocessing can significantly transform the translation unit before it reaches the parser.

ComplyC therefore contains source-mapping support designed to map analyzer findings back toward the original source file and source location.

Source mapping is actively being improved during the beta phase.

Complex macro expansion, generated declarations, conditional compilation, and some included-header constructs may still produce imperfect attribution.

---

## Control-Flow and Dataflow Infrastructure

The project currently contains infrastructure for:

* Control-Flow Graph (CFG) construction
* Cyclomatic-complexity calculation
* Basic dataflow analysis
* Source-level call-graph analysis

Some of these capabilities are still experimental and are not intended to represent production-grade whole-program analysis in the current beta.

---

## Beta Rule Coverage

ComplyC `v0.9.0-beta` is intentionally scoped to a defined set of coding-guideline checks. The purpose of documenting the checks below is to make the beta boundary explicit: reviewers should know what ComplyC currently evaluates and should not assume that the tool performs checks that are not listed here.

### Implemented Check Handlers

The current rule engine contains the following implemented handlers:

| Check Handler | What It Checks |
|---|---|
| `regex` | Validates supported identifiers against a configured regular-expression naming pattern. |
| `global_naming` | Validates naming conventions for global variables. |
| `max_function_length` | Reports functions that exceed the configured maximum source-line length. |
| `max_parameter_count` | Reports functions with more than the configured number of parameters. |
| `forbidden_functions` | Detects calls to functions explicitly prohibited by the active YAML rule. |
| `file_header_contains` | Checks whether required information is present in the source-file header. |
| `max_cyclomatic_complexity` | Calculates function cyclomatic complexity and reports values above the configured threshold. |
| `max_nesting_depth` | Reports functions whose control-flow nesting exceeds the configured depth. |
| `no_assignment_in_condition` | Detects assignments used inside conditional expressions. |
| `switch_requires_default` | Checks that a `switch` statement contains a `default` label. |
| `no_empty_statement` | Detects empty statements in supported control-flow constructs. |
| `no_empty_block` | Detects empty control blocks unless accepted by the rule's intentional-empty handling. |
| `no_unreachable_code` | Detects supported cases of statements that occur after unconditional control transfer. |
| `no_implicit_fallthrough` | Detects supported `switch` cases that fall through without an accepted explicit indication. |
| `forbid_keyword` | Detects prohibited language keywords configured by a rule, currently used for `goto`. |
| `empty_function_body` | Detects functions with an empty body or no executable implementation. |
| `no_infinite_loops` | Detects supported forms of intentionally or accidentally unbounded loops according to the configured rule. |
| `max_length` | Checks supported identifiers against a configured maximum character length. |
| `forbid_single_letter` | Detects prohibited single-character variable names. |
| `elseif_must_end_with_else` | Checks that an `if` / `else if` chain terminates with a final `else`. |
| `require_braces` | Checks that supported control-statement bodies use curly braces. |
| `brace_own_line` | Checks the configured opening-brace placement convention. |
| `no_recursion` | Detects direct recursion using the current function/call analysis. |

A check handler being available in the engine does not automatically mean that every possible variation of that check is enabled in the default YAML rule set. Rules remain configuration-driven.

### Default Beta Coding Rules

The supplied `rules/complyc_style.yml` currently configures the following implemented beta checks:

| Rule ID | Beta Check |
|---|---|
| `NAMING_FUNC_001` | Function names follow the configured `lower_snake_case` pattern. |
| `NAMING_GLOBAL_001` | Global variables use the configured `g_` naming convention. |
| `NAMING_STATIC_001` | File-static variables use the configured `s_` naming convention. |
| `NAMING_VAR_003` | Variable names do not exceed 31 characters. |
| `NAMING_VAR_004` | Single-letter variable names are rejected. |
| `FILE_HEADER_001` | C files contain the required standard header information. |
| `FORMAT_BRACE_001` | Control bodies use curly braces. |
| `BRACE_STYLE_002` | Opening braces follow the configured own-line style. |
| `SAFETY_RECURSION_001` | Direct recursion is forbidden. |
| `SAFETY_DYNAMIC_MEM_001` | Dynamic heap APIs are forbidden. |
| `LOOP_INFINITE_001` | Supported infinite-loop forms are reported. |
| `FORBIDDEN_GOTO_001` | Use of `goto` is forbidden. |
| `CTRL_ELSEIF_001` | `if` / `else if` chains require a terminating `else`. |
| `FUNC_SIZE_001` | Functions are limited to 40 lines. |
| `FUNC_CC_001` | Cyclomatic complexity is limited to 10. |
| `FUNC_NESTING_001` | Nesting depth is limited to 4. |
| `FUNC_PARAMS_001` | Functions are limited to 6 parameters. |
| `DEAD_CODE_EMPTY_FUNC_001` | Empty function bodies are reported. |
| `MISRA_LITE_ASSIGN_COND_001` | Assignment inside conditional expressions is forbidden. |
| `DEAD_CODE_EMPTY_STMT_001` | Empty statements are reported. |
| `CTRL_EMPTY_BLOCK_001` | Empty control blocks require intentional-empty handling. |
| `CTRL_SWITCH_DEFAULT_001` | `switch` statements require a `default` label. |
| `CTRL_SWITCH_FALLTHROUGH_001` | Implicit `switch` fall-through is forbidden. |
| `DEAD_CODE_UNREACHABLE_001` | Supported unreachable-code patterns are reported. |
| `SAFETY_FORBIDDEN_API_001` | Configured unsafe C library APIs are forbidden. |

### Limited Security-Oriented Checks

Cybersecurity analysis in `v0.9.0-beta` is deliberately limited. ComplyC is **not** claiming to be a complete secure-C, CERT C, CWE, vulnerability-scanning, or cybersecurity-compliance product in this release.

The current security-oriented checks are:

#### `SAFETY_DYNAMIC_MEM_001` — Dynamic Memory

Reports calls to:

```text
malloc
calloc
realloc
free
```

This rule is intended to identify use of dynamic heap allocation where the project's safety/coding policy prohibits it.

#### `SAFETY_FORBIDDEN_API_001` — Unsafe or Restricted C Library APIs

Reports calls to the following functions configured in the current YAML:

```text
gets
strcpy
strncpy
strcat
strncat
sprintf
vsprintf
scanf
sscanf
fscanf
```

The purpose is to flag APIs that the project coding policy requires engineers to replace with bounded or project-approved alternatives.

#### `SAFETY_RECURSION_001` — Recursion

Reports direct recursive function calls. In embedded and safety-oriented projects, recursion may be prohibited because of stack-usage predictability and execution-resource constraints.

### Security Compliance in the HTML Report

The HTML report includes a **Security-Oriented Findings (Limited Beta Checks)** compliance chart.

The security percentage is calculated only against the limited security rules represented by that report metric. A clean result means that no violations were detected by those configured checks; it **does not mean that the analyzed software is free of cybersecurity vulnerabilities**.

The report also contains a **Rule Summary Findings** chart showing the distribution of all detected violations by severity, followed by the detailed rule-by-rule summary.

### Configured Rules Not Yet Active in This Beta

The supplied YAML also contains rules that are planned/configured but are not currently executable through the complete rule-dispatch path. They should not be interpreted as active beta checks:

| Rule ID | Reason |
|---|---|
| `DOC_FUNC_001` | References the `preceding_comment` handler, which is not currently registered in `CHECK_HANDLERS`. |
| `FIXEDPOINT_COMMENT_001` | Uses the unsupported `expression` scope and references `binary_point_comment_required`, which is not currently registered. |
| `FORMAT_INDENT_001` | References `consistent_indentation`, which is not currently registered in `CHECK_HANDLERS`. |

These entries are retained as development targets, but community reviewers should evaluate the beta based on the implemented checks documented above.

> ComplyC rules described as MISRA-inspired, CERT-inspired, safety-oriented, or security-oriented are project checks inspired by those engineering practices. They do not constitute certification or complete compliance with those standards.

---

## Reports

ComplyC currently supports:

* **HTML**
* **JSON**
* **CSV**

The HTML report provides a human-readable engineering summary including:

* Files scanned and total violations
* Severity totals
* **Security-Oriented Findings** compliance chart for the limited beta security checks
* **Rule Summary Findings** severity-distribution chart
* Detailed rule summary with per-rule contribution to total findings
* Per-file violations
* Rule ID and severity
* Original source location where available
* Violation message and coding-guideline reference

JSON and CSV output are available for additional processing, metrics, review records, and future CI/CD integration.

---

## Graphical User Interface

ComplyC includes a Windows-oriented graphical interface for running compliance scans without requiring command-line interaction.

The GUI supports:

* Selecting C and header files
* Selecting a YAML rule configuration
* Built-in or GCC preprocessing
* Automatic project discovery
* Include-directory configuration
* Preprocessor definitions
* Compliance scanning
* Violation review
* In-GUI violation filtering by **File**, **Rule ID**, and **Severity**
* Free-text violation search across displayed finding information
* Dynamic **Showing X of Y violations** result count
* **Clear Filters** control
* Double-click navigation from a filtered violation to the original source file and line
* HTML report generation
* CSV report generation
* Opening generated reports

Run the GUI from source with:

```bash
python complyc_gui.py
```

On Windows, you can also use:

```text
RUN_FROM_SOURCE.bat
```

---

# Architecture Overview

The current analysis pipeline can be summarized as:

```text
C / Header Files
       |
       v
Project Discovery
       |
       v
Include Paths / Defines
       |
       v
Preprocessing
  |           |
  |           +--> Built-in preprocessing
  |
  +--------------> GCC preprocessing
       |
       v
Compiler Extension Sanitization
       |
       v
Type Recovery
       |
       v
pycparser AST
       |
       +--------------------+
       |                    |
       v                    v
Source Index          CFG / Dataflow
       |                    |
       +----------+---------+
                  |
                  v
             Rule Engine
                  |
                  v
            Source Mapping
                  |
                  v
        Compliance Violations
                  |
          +-------+-------+
          |       |       |
          v       v       v
        HTML     JSON     CSV
```

The architecture intentionally separates preprocessing, parsing, source indexing, analysis, rule evaluation, and reporting so individual components can evolve independently.

---

# Project Structure

A simplified view of the current project structure is:

```text
ComplyC/
|
├── complyc/
│   ├── __init__.py
│   ├── cfg.py
│   ├── compiler_extensions.py
│   ├── dataflow.py
│   ├── loader.py
│   ├── main.py
│   ├── parser.py
│   ├── project_discovery.py
│   ├── reporters.py
│   ├── rule_engine.py
│   ├── scan_worker.py
│   ├── source_callgraph.py
│   ├── source_index_engine.py
│   ├── source_mapping.py
│   └── type_recovery.py
│
├── rules/
│   └── complyc_style.yml
│
├── fake_libc_include/
│
├── examples/
│   ├── sample_good.c
│   ├── sample_bad.c
│   └── additional rule examples
│
├── tests/
│   ├── regression/
│   └── test_source_index_engine.py
│
├── docs/
│
├── complyc_gui.py
├── complyc_scan_worker.py
├── RUN_FROM_SOURCE.bat
├── build_windows_exe.bat
├── requirements.txt
└── BUILD_INSTRUCTIONS.md
```

---

# Requirements

The current Python dependencies are:

```text
pycparser>=2.22
PyYAML>=6.0.1
pyinstaller>=6.0
```

Python **3.11 or 3.12** is recommended for the current Windows beta.

For GCC preprocessing, a compatible GCC installation must also be available on the system `PATH`.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/Kishore-Gorijavolu/ComplyC.git
cd ComplyC/ComplyC
```

Create a virtual environment if desired:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

---

# Running the GUI

The easiest way to evaluate ComplyC is through the GUI.

On Windows:

```text
RUN_FROM_SOURCE.bat
```

Or:

```bash
python complyc_gui.py
```

Typical workflow:

1. Select the YAML rule file.
2. Add one or more C/header files.
3. Select the required preprocessing mode.
4. Configure or auto-detect include paths.
5. Configure required preprocessor definitions.
6. Run the compliance scan.
7. Review detected violations.
8. Filter findings by file, rule ID, severity, or free-text search as needed.
9. Double-click a visible violation to navigate to the corresponding source location.
10. Open the generated HTML or CSV report when a persistent review artifact is required.

For embedded projects that depend heavily on vendor headers and conditional compilation, GCC preprocessing is generally the more representative analysis path.

---

# Command-Line Usage

ComplyC can also be executed through the Python module interface.

## Analyze a Source File

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    path/to/source.c
```

On Windows CMD, the same command can be entered on one line:

```bat
python -m complyc.main --rules rules/complyc_style.yml path\to\source.c
```

---

## Generate an HTML Report

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    --html-report reports/report.html \
    path/to/source.c
```

---

## Generate a JSON Report

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    --json-report reports/report.json \
    path/to/source.c
```

---

## Force GCC Preprocessing

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    --use-gcc \
    path/to/source.c
```

---

## Force Built-in Preprocessing

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    --no-gcc \
    path/to/source.c
```

---

## Quiet Mode

To suppress detailed per-file console output:

```bash
python -m complyc.main \
    --rules rules/complyc_style.yml \
    --quiet \
    path/to/source.c
```

---

# Windows Executable

A standalone Windows executable can be generated using PyInstaller.

Run:

```text
build_windows_exe.bat
```

or follow:

```text
BUILD_INSTRUCTIONS.md
```

The generated executable is placed under:

```text
dist\ComplyC-GUI.exe
```

A packaged executable should always be rebuilt from the corresponding release source before distribution.

---

# Example Files

The `examples/` directory contains intentionally compliant and non-compliant C files that can be used to evaluate the analyzer.

Start with:

```text
examples/sample_good.c
examples/sample_bad.c
```

Additional examples exercise individual coding-rule scenarios.

---

# Current Beta Limitations

ComplyC is under active development.

Community reviewers should expect limitations around:

* Complex macro expansion
* Compiler-specific constructs not yet handled by the sanitizer
* Vendor-specific preprocessing environments
* Header/source attribution in complex translation units
* Generated source code
* Advanced dataflow analysis
* Cross-translation-unit analysis
* Some source-line reconstruction scenarios
* Incomplete rule-handler coverage
* Potential false positives or false negatives

The analyzer should therefore be treated as an **engineering-assistance and coding-guideline compliance tool**, not as the sole basis for safety certification or production release approval.

Please report reproducible cases where ComplyC:

* Fails to preprocess valid embedded C
* Fails to parse valid preprocessed C
* Reports an incorrect source line
* Confuses local, static, global, or parameter declarations
* Produces a false positive
* Misses an expected violation
* Crashes or hangs
* Produces an incorrect report

These cases are particularly valuable during the beta phase.

---

# Project Goals

The primary objective of ComplyC is **not to replace a compiler or become a general-purpose compiler frontend**.

Its goal is to provide a practical framework for:

> **Validating embedded C source code against configurable organization-specific coding guidelines.**

Longer-term development may extend the analyzer with:

* Additional coding-rule handlers
* Improved source mapping
* Improved symbol resolution
* Cross-reference analysis
* Enhanced CFG/dataflow analysis
* Rule suppression mechanisms
* MISRA-inspired rule packs
* AUTOSAR-inspired rule packs
* Security-focused rule packs
* CI/CD integration
* Improved project configuration
* Additional reporting and developer workflow integrations

Planned functionality should not be interpreted as currently implemented functionality.

---

# Community Beta Review

ComplyC `v0.9.0-beta` is being made available for engineering review and practical testing.

Feedback is especially useful from developers working with:

* Embedded C
* Automotive software
* Microcontroller firmware
* Bootloaders
* Device drivers
* Safety-related software
* Coding-standard compliance
* Software unit verification
* Static-analysis tooling

Useful feedback includes:

* Reproducible defects
* Parser/preprocessor failures
* Incorrect findings
* Missing findings
* Rule-engine limitations
* Embedded-project compatibility issues
* Reporting issues
* Architecture observations
* Rule proposals
* Test cases and regression examples

When reporting a problem, please provide the smallest source example that reproduces the behavior whenever possible.

---

# Contributing

Community contributions are welcome.

Useful contributions include:

* Bug reports
* Regression tests
* Embedded-C compatibility examples
* Rule-handler implementations
* Parser and preprocessing improvements
* Source-mapping improvements
* Documentation
* Reporting improvements

For significant changes, please open an issue or discussion describing the proposed change before submitting a large pull request.

---

# License

ComplyC is released under the **MIT License**.

See `LICENSE` for the complete license text.

---

# Disclaimer

ComplyC is an independent open-source software project.

It is not a certified functional-safety verification tool and does not by itself establish compliance with MISRA C, AUTOSAR C, ISO 26262, Automotive SPICE, IEC 61508, or any other industry standard.

Users remain responsible for determining whether the tool and its results are appropriate for their development, verification, compliance, or certification activities.

---

# Contact

**Project:** ComplyC

**Author:** Kishore Gorijavolu

GitHub:
https://github.com/Kishore-Gorijavolu

LinkedIn:
https://www.linkedin.com/in/gokish03
