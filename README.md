# ComplyC – Coding Guideline Compliance Engine for C

ComplyC is a lightweight tool that helps teams automatically check whether their C code follows internal coding guidelines.

Instead of manually reviewing style, structure, and safety rules, ComplyC turns those guidelines into executable checks and generates clear reports of violations.

It is designed for embedded and safety-critical development workflows where consistency, traceability, and audit readiness matter.

---

# What problem this solves

In most teams:

* Coding guidelines exist as documents (PDF, Word, Confluence)
* Enforcement depends on manual reviews
* Violations slip through or are inconsistently applied

ComplyC closes that gap by:

> Converting coding rules into automated checks that run on real code.

---

# What ComplyC does

ComplyC scans `.c` and `.h` files and validates them against a configurable rule set.

It can detect things like:

* Naming convention violations
* Missing file headers or documentation blocks
* Magic numbers in code
* Forbidden functions or constructs
* Function size, complexity, and structure issues
* Basic dataflow issues (e.g., unused variables, dead stores)

Example:

```c
int a = 10;     // flagged as magic number
return 42;      // flagged as magic number
```

These are not syntax errors—but they violate maintainability rules.

---

# ⚠️ What ComplyC is NOT

ComplyC is **not a MISRA static analysis tool**.

* It does not aim to fully enforce MISRA C
* It does not perform deep compiler-level semantic validation
* It does not replace tools like Polyspace, Coverity, or PC-Lint

Instead:

> ComplyC focuses on enforcing **organization-specific coding standards**, which is a different layer of software quality.

---

# How it works

At a high level:

1. Load rules from a YAML file
2. Parse C source into an AST
3. Apply rules based on scope (file, function, variable, etc.)
4. Generate structured reports

The engine is modular:

* Parser (pycparser + optional GCC preprocessing)
* Rule engine (pluggable checks)
* CFG + basic dataflow analysis
* Report generators (HTML, JSON)

---

# Example rule (YAML)

```yaml
- id: NAMING_001
  title: "Function names must be lower_snake_case"
  scope: function
  check: regex
  pattern: "^[a-z][a-z0-9_]*$"
  severity: major
  guidance: "Rename function to match naming convention"
```

---

# Output

ComplyC generates clean reports that can be used for reviews or audits.

Includes:

* Total violations
* Severity breakdown
* File + line reference
* Rule ID and description
* Suggested fix guidance

Formats:

* HTML (review-friendly)
* JSON (tool integration)
* CSV (metrics / audits)

---

# Where this fits in the workflow

ComplyC fits naturally into:

* Code reviews (pre-check before PR)
* CI/CD pipelines
* ASPICE SWE.4 / SWE.5 activities
* Internal compliance audits

It helps answer:

> “Is this code following our coding standard consistently?”

---

# Getting started

Install dependencies:

```bash
pip install clang pyyaml rich
```

Run on a file:

```bash
python -m complyc.main --rules rules/complyc_style.yml src/file.c
```

Generate report:

```bash
python -m complyc.main --rules rules/complyc_style.yml src/*.c --html-report report.html
```

---

# 📁 Project structure

```
complyc/
  parser.py
  rule_engine.py
  cfg.py
  dataflow.py
  reporters.py

rules/
  complyc_style.yml

examples/
  sample_code.c
```

---

# Why this project

This project started from a simple observation:

> Teams spend a lot of time writing coding guidelines—but very little time enforcing them consistently.

ComplyC is an attempt to bridge that gap in a practical, configurable way.

---

# Roadmap

Planned improvements:

* More rule templates (automotive / embedded)
* Better reporting UI
* Clang-based parsing option
* Deeper dataflow checks
* CI/CD integrations

---

# Contributing

Contributions are welcome:

* Add new rules
* Improve analysis checks
* Enhance reporting
* Extend parser support

---

# 📬 Contact

Kishore Gorijavolu
* LinkedIn: [https://www.linkedin.com/in/gokish03](https://www.linkedin.com/in/gokish03)
* GitHub: [https://github.com/Kishore-Gorijavolu](https://github.com/Kishore-Gorijavolu)

---
