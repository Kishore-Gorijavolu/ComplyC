# ComplyC Roadmap

## Vision

Build an open-source static analysis and coding-guideline compliance tool focused on Embedded C, configurable coding standards, and safety-critical software development.

# Version 0.9 -- Community Beta

* Core YAML-driven rule engine
* AST-based C source analysis
* Configurable coding-guideline rules
* Naming and formatting checks
* Complexity and function-size checks
* Control-flow and dead-code checks
* Basic safety and security checks
* GCC preprocessing support
* Compiler-extension sanitization
* Vendor-header recovery
* Source Mapping Engine
* Original source file/line reporting
* HTML, JSON, and CSV reporting
* Rule and Security Summary
* Windows desktop GUI
* Violation filtering
* Open source file at violation

# Version 1.0 -- Stability & Community Feedback

* Community-reported bug fixes
* False-positive reduction
* Preprocessor reliability improvements
* Source-mapping improvements
* Additional compiler-extension support
* Improved diagnostic messages
* GUI stability improvements
* Regression tests for reported defects
* Large embedded-project validation
* Release packaging improvements

**Goal:** Stable community release with no known critical scanner or reporting defects.

# Version 1.1 -- Security Rule Pack

* Dedicated `SEC_*` security rules
* CWE mappings
* Unsafe input detection
* Unsafe string-operation detection
* Format-string checks
* Command-execution API detection
* Weak/insecure API detection
* Hard-coded secret detection
* Constant array-bounds checks
* Divide-by-zero checks
* Invalid shift detection
* Security-focused HTML reporting

**Goal:** High-confidence security checks with automated positive and negative test cases.

# Version 1.2 -- Coding Rule Expansion

* Magic-number detection
* Function documentation rules
* Configurable indentation rules
* Fixed-point documentation checks
* Additional embedded C coding rules
* Improved custom rule configuration
* Rule suppression support
* Project-specific rule packs

**Goal:** Expand ComplyC's ability to enforce organization and project-specific coding guidelines.

# Version 1.3 -- Dataflow & Static Analysis

* Improved Control Flow Graph (CFG)
* Definite initialization analysis
* Uninitialized variable detection
* Unused variable detection
* Dead-store detection
* Improved symbol resolution
* Function call graph
* Cross-file analysis

**Goal:** Introduce deeper static analysis while maintaining low false-positive rates.

# Version 1.4 -- CI/CD Integration

* Headless command-line scanning
* Standardized process exit codes
* Configurable quality gates
* GitHub Actions integration
* Jenkins integration
* GitLab CI/CD support
* Bitbucket Pipelines support
* Azure DevOps support
* Machine-readable CI reports

**Goal:** Allow ComplyC to operate as an automated coding-compliance gate.

# Future

Potential future improvements based on community interest:

* MISRA-oriented rule expansion
* CERT C-oriented security rules
* AUTOSAR-oriented coding checks
* Baseline existing violations
* Incremental scanning
* Cross-project analysis
* Performance optimization
* Additional compiler/toolchain support
* IDE/editor integration
* Additional community rule packs

---

## Development Principles

* Accuracy before rule count
* Low false-positive rates
* Configurable rules instead of project-specific hard-coding
* Clear source traceability
* Practical Embedded C support
* Automated regression testing
* Transparent documentation of limitations

> Roadmap priorities and version assignments may change based on community feedback, testing results, and project requirements.
