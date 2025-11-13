# ComplyC — A Configurable Coding Guideline Compliance Engine for Safety-Critical C Code  
### Rule-Based Static Analysis for Automotive & Embedded Systems

ComplyC is a lightweight, configurable, standards-aware coding-guideline compliance engine designed for safety-critical embedded C projects.

It transforms natural-language coding guidelines into **executable rules** and automatically analyzes `.c` and `.h` files for deviations.

Whether you're working with automotive inverters (HVPO, HVDC), bootloaders, microcontroller firmware, or ASPICE SWE.4–SWE.6 deliverables, ComplyC enforces **consistency, safety, and traceability** from Day 1.

---

## 🚀 Key Features

### 🔍 1. Rule-Based Coding Guideline Enforcement
ComplyC parses your source code and checks it against your team’s style guide, including:

- Function & variable naming conventions  
- Required module header templates  
- Commenting & documentation rules (Doxygen, inline docs)  
- Bracing & indentation style  
- Global/static variable restrictions  
- Forbidden constructs (recursion, dynamic memory, `goto`)  
- Safety-critical checks:  
  - magic numbers  
  - unguarded array writes  
  - hardware-register access patterns  

Rules are stored as **clean, editable YAML** for easy customization.

---

### 📄 2. Detailed Non-Compliance Reports
ComplyC produces clean, actionable reports:

- Total violations  
- Violations by severity (critical / major / minor)  
- Rule ID, description, guideline reference  
- File name, line number, code snippet  
- Recommended fix  

**Supported output formats:**

- **HTML** – ideal for JIRA & code reviews  
- **Markdown** – GitHub friendly  
- **JSON** – CI/CD integration  
- **CSV** – audit-ready compliance metrics  

---

### 🧠 3. AST-Aware Static Analysis (libclang)
Powered by Clang’s AST for accurate detection of:

- Function declarations/definitions  
- Control structures (`if`, `for`, `while`, `switch`)  
- Typedefs, enums, macros  
- File metadata  
- Nested scopes & code blocks  

This ensures deep structural analysis far beyond regex-based linters.

---

### 🧩 4. Integrates Seamlessly With Automotive Workflows

- ASPICE V-Model compliance  
- SWE.4 Unit Design & Implementation  
- SWE.5 Unit Verification  
- SWE.6 Integration & Testing  
- ISO 26262 Part 6  
- CI/CD (GitLab, GitHub Actions, Azure DevOps)  

---

### ⚙️ 5. Fully Customizable Rule Sets
Example YAML rule:

```yaml
- id: NAMING_001
  title: "Function names must be in lower_snake_case"
  scope: function
  pattern: "^[a-z][a-z0-9_]*$"
  severity: major
  guidance: "Rename function to comply with naming standard."
  reference: "Coding Guideline §3.2.1"

You can define:
•	Naming conventions
•	Forbidden APIs
•	Required comments
•	Safety rules (e.g., no unchecked boundary conditions)
•	Formatting rules
________________________________________
🛠️ Installation
•	Installation Guide and basic command will be provided (Refer to User Guide)

Install dependencies
pip install clang pyyaml rich
Clone the repository
git clone https://github.com/<your-username>/ComplyC.git
cd ComplyC
________________________________________
▶️ Usage
Basic run
python -m complyc.main --rules rules/complyc_style.yml <folder_name>/<yourfile>.c
Example: python -m complyc.main --rules rules/complyc_style.yml examples/sample_bad.c

________________________________________
ComplyC/
│
├── complyc/
│   ├── parser.py             # libclang AST parser
│   ├── rule_engine.py        # Rule evaluation engine
│   ├── report_generator.py   # HTML/Markdown/JSON reports
│   ├── scanner.py            # Orchestrates workflow
│   └── utils.py              # Helper utilities
│
├── rules/
│   └── example_style.yml     # Sample rule set
│
├── examples/
│   └── sample_code.c         # Demo source file
│
└── README.md

________________________________________
📊 Sample Report Output
Summary
Severity	Count
Critical	1
Major	6
Minor	12
Example Violation
File: src/mod_nvm.c
Line: 87
Rule: NAMING_001 – Function names must be in lower_snake_case
Message: Function 'RomCalcCrc16' does not match required naming convention.
Guideline: Coding Guideline §3.2.1
Suggested Fix: Rename to 'rom_calc_crc16'
________________________________________
🌐 Use Cases
•	Automotive embedded C (inverter, BMS, ADAS, chargers)
•	Aerospace firmware compliance
•	Industrial controls & power electronics
•	Medical device firmware review
•	Bootloader & memory management modules
•	Any team with a formal coding standard
________________________________________
🏆 Why This Project Matters 
ComplyC demonstrates:
•	Original contribution to the safety-critical software engineering field
•	Practical impact on embedded systems quality & reliability
•	Innovation: converting natural-language standards into executable rules
•	Adoption potential across industries and engineering teams
•	Leadership in automated static compliance checking
________________________________________
🤝 Contributing
Pull requests and feature suggestions are welcome!
Feel free to add new rule templates, parsers, or language support.
________________________________________
📜 License
MIT License.
Use freely in both commercial and academic environments.
________________________________________
📬 Contact
For questions, contributions, or enterprise integration:
Email: kishore.gorijavolu@gmail.com
LinkedIn: https://www.linkedin.com/in/gokish03
GitHub: kishore-gorijavolu

