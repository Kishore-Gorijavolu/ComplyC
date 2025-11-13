# ComplyC — A Configurable Coding Guideline Compliance Engine for Safety-Critical C Code
### Rule-Based Static Analysis for Automotive & Embedded Systems

ComplyC is a lightweight, configurable, standards-aware coding-guideline compliance engine designed for safety-critical embedded C projects.

It transforms natural-language coding guidelines into **executable rules** and automatically analyzes `.c` and `.h` files for deviations.

Whether you're working with automotive inverters (HVPO, HVDC), bootloaders, microcontroller firmware, or ASPICE SWE.4–SWE.6 deliverables, ComplyC enforces **consistency, safety, and traceability** from Day 1.

---

## 🚀 Key Features

### 🔍 1. Rule-Based Coding Guideline Enforcement
ComplyC parses your source code and validates it against your organization's coding-style guide, including:

- Function & variable naming conventions  
- Required module header templates  
- Commenting & documentation rules (Doxygen, inline docs)  
- Bracing & indentation style  
- Global/static variable restrictions  
- Forbidden constructs (recursion, dynamic memory, `goto`)  
- Safety-critical checks:  
  - magic numbers  
  - unguarded array writes  
  - unsafe hardware-register access  
  - missing boundary checks  

Rules are stored in **clean, editable YAML**, making it easy for teams to evolve their standards.

---

##  2. Detailed Non-Compliance Reports

ComplyC generates clean, audit-ready compliance reports:

- Total violations  
- Violations by severity (critical / major / minor)  
- Rule ID, title, guidance, and standard reference  
- File name, line number, highlighted snippet  
- Recommended fix for each violation  

**Supported output formats:**

- **HTML** – ideal for JIRA uploads & design reviews  
- **Markdown** – GitHub-friendly  
- **JSON** – toolchain & CI/CD integration  
- **CSV** – compliance metrics for ASPICE & ISO 26262 audits  

---

##  3. AST-Aware Static Analysis (via libclang)

Built on Clang’s AST, enabling precise structural analysis far beyond regex-based linters:

- Function declarations & definitions  
- Control structures (`if`, `switch`, `for`, `while`)  
- Typedefs, enums, macros  
- File-level metadata  
- Nested scopes, blocks, and variable lifetimes  

This ensures **accurate and deterministic rule enforcement** even in complex embedded projects.

---

##  4. Automotive & Safety Workflow Integration

ComplyC integrates naturally into:

- ASPICE V-Model  
- SWE.4 — Unit Design & Implementation  
- SWE.5 — Unit Verification  
- SWE.6 — Integration & Testing  
- ISO 26262 Part 6 safety software workflow  
- CI/CD (GitLab, GitHub Actions, Azure DevOps)  

---

##  5. Configurable YAML Rule Sets

Example rule:

```yaml
- id: NAMING_001
  title: "Function names must be in lower_snake_case"
  scope: function
  pattern: "^[a-z][a-z0-9_]*$"
  severity: major
  guidance: "Rename function to comply with the naming standard."
  reference: "Coding Guideline §3.2.1"
```

You can define:

- Naming conventions  
- Forbidden APIs  
- Required documentation blocks  
- Safety rules (bounds, range checks, MISRA-like constraints)  
- Formatting rules  

---

#  Installation

### Install Dependencies
```bash
pip install clang pyyaml rich
```

### Clone the Repository
```bash
git clone https://github.com/<your-username>/ComplyC.git
cd ComplyC
```

---

#  Usage

### Basic Run
```bash
python -m complyc.main --rules rules/complyc_style.yml path/to/file.c
```

### Scan Entire Project
```bash
python -m complyc.main --rules rules/complyc_style.yml src/**/*.c
```

### Save an HTML Report
```bash
python -m complyc.main --rules rules/complyc_style.yml src/*.c --report out/report.html
```

---

#  Directory Structure

```
ComplyC/
│
├── complyc/
│   ├── parser.py             # libclang AST parser
│   ├── rule_engine.py        # Rule evaluation engine
│   ├── report_generator.py   # HTML/MD/JSON/CSV reports
│   ├── scanner.py            # Orchestrates the rule-checking workflow
│   └── utils.py              # Helper utilities
│
├── rules/
│   └── example_style.yml     # Sample rule set
│
├── examples/
│   └── sample_code.c         # Demo input file
│
└── README.md
```

---

#  Sample Report Output

### Summary

| Severity | Count |
|---------|-------|
| Critical | 1 |
| Major | 6 |
| Minor | 12 |

---

### Example Violation

```
File: src/mod_nvm.c
Line: 87
Rule: NAMING_001 – Function names must be in lower_snake_case
Message: Function 'RomCalcCrc16' does not match required naming convention.
Guideline: Coding Guideline §3.2.1
Suggested Fix: Rename to 'rom_calc_crc16'
```

---

#  Use Cases

- Automotive embedded C (inverters, BMS, ADAS, chargers)  
- Aerospace firmware verification  
- Industrial controllers & power electronics  
- Medical device firmware compliance  
- Bootloaders & memory-management modules  
- Any organization with a formal coding standard  

---

#  Why This Project Matters

ComplyC demonstrates:

- **Original technical contribution** to safety-critical software engineering  
- **Improved reliability** in embedded systems  
- **Innovation**: converting natural-language rules → executable validation  
- **Industry adoption potential** across automotive, aerospace, medical, industrial  
- **Leadership** in automated static-compliance tooling  


---

#  Contributing

Contributions are welcome!  
You may add:

- New rule templates  
- Extended AST parsers  
- Additional reporting formats  
- Multi-language support  

Submit a PR anytime.

---

#  License

Released under the **MIT License**.  
Free for commercial and academic use.

---

# 📬 Contact

**Email:** kishore.gorijavolu@gmail.com  
**LinkedIn:** https://www.linkedin.com/in/gokish03  
**GitHub:** https://github.com/kishore-gorijavolu  
