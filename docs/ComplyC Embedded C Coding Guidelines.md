# ComplyC Embedded C Coding Guidelines

## Practical Coding Rules for Reliable, Maintainable, and Safety-Conscious Embedded C

**Beta Edition — Version 0.9**

ComplyC Project

---

# About This Guide

The **ComplyC Embedded C Coding Guidelines** provide a practical coding standard for developers working with C, particularly in embedded and safety-conscious software projects.

The guide focuses on coding practices that improve:

- readability;
- maintainability;
- predictability;
- static analyzability;
- defect prevention;
- code-review consistency; and
- software quality.

Many guidelines in this document can be checked automatically using **ComplyC**.

ComplyC is not intended to replace formal standards such as MISRA C, CERT C, AUTOSAR C++14, ISO 26262, or an organization's engineering process. It provides an accessible automated layer for detecting common coding-style, maintainability, control-flow, and safety-related issues.

---

# 1. Guideline Classification

Each guideline uses one of the following classifications.

| Classification | Meaning |
|---|---|
| **Required** | Expected for ComplyC-compliant source code |
| **Recommended** | Strongly encouraged engineering practice |
| **Advisory** | Useful practice depending on project constraints |

Where applicable, the corresponding **ComplyC Rule ID** is provided.

---

# 2. Naming Conventions

## 2.1 Function Names

**Required**

Functions shall use descriptive `lower_snake_case` names.

### Preferred

```c
uint16_t calculate_crc(void);
void update_motor_state(void);
bool is_voltage_valid(void);
```

### Avoid

```c
uint16_t CalculateCRC(void);
void updateMotorState(void);
void func1(void);
```

Function names should normally describe an action.

**ComplyC Rule:** `NAMING_FUNC_001`

---

## 2.2 Global Variables

**Required**

Global variables shall begin with `g_`.

```c
uint16_t g_system_voltage;
bool g_system_initialized;
```

Avoid global variables where practical because they increase coupling and make state changes harder to trace.

**ComplyC Rule:** `NAMING_GLOBAL_001`

---

## 2.3 File-Static Variables

**Required**

File-local static variables shall begin with `s_`.

```c
static uint16_t s_retry_count;
static bool s_initialized;
```

The prefix immediately communicates that the object has file scope.

**ComplyC Rule:** `NAMING_STATIC_001`

---

## 2.4 Macro Names

**Required**

Macro names shall use `UPPER_SNAKE_CASE`.

```c
#define MAX_RETRY_COUNT     3U
#define ADC_TIMEOUT_MS      100U
#define SYSTEM_ERROR_MASK   0x04U
```

Avoid:

```c
#define maxRetryCount 3
#define Timeout 100
```

**ComplyC Rule:** `NAMING_MACRO_001`

---

## 2.5 Variable Names

**Recommended**

Variable names should communicate their purpose.

Prefer:

```c
uint16_t retry_count;
uint32_t timeout_ms;
uint16_t battery_voltage_mv;
```

over:

```c
uint16_t x;
uint32_t val;
uint16_t temp;
```

Single-letter identifiers should normally be avoided except for conventional short-lived loop counters such as `i`, `j`, and `k`.

**ComplyC Rule:** `NAMING_VAR_004`

---

## 2.6 Identifier Length

**Required by the default ComplyC profile**

Variable names shall not exceed the configured identifier-length limit.

The current ComplyC default profile uses **31 characters**.

**ComplyC Rule:** `NAMING_VAR_003`

---

## 2.7 Include Units in Names

**Recommended**

Where a variable represents a physical quantity, include the unit where doing so prevents ambiguity.

```c
uint32_t timeout_ms;
uint16_t voltage_mv;
uint32_t frequency_hz;
uint16_t temperature_deg_c;
```

Avoid ambiguous names such as:

```c
uint32_t timeout;
uint16_t voltage;
```

This is especially useful in embedded software where unit mismatches can produce serious defects.

---

# 3. Source File Documentation

## 3.1 File Header

**Required**

Every C source file should begin with a standard module header.

Example:

```c
/******************************************************************************
 * Module Name: VoltageMonitor
 * Description: Monitors supply voltage and reports diagnostic faults.
 * Author: ComplyC Project
 * Version: 1.0
 ******************************************************************************/
```

At minimum, the default ComplyC configuration expects:

- Module Name
- Description
- Author
- Version

**ComplyC Rule:** `FILE_HEADER_001`

---

## 3.2 Comments Explain Why

**Recommended**

Comments should explain engineering intent, assumptions, limitations, or non-obvious decisions.

Avoid:

```c
/* Increment counter */
counter++;
```

Prefer:

```c
/* Require three consecutive failures before reporting the diagnostic. */
failure_count++;
```

The source code already describes **what** is happening. Comments should normally explain **why**.

---

# 4. Formatting

## 4.1 Braces Are Mandatory

**Required**

Control-flow bodies shall use braces.

Preferred:

```c
if (system_ready)
{
    start_control();
}
```

Avoid:

```c
if (system_ready)
    start_control();
```

Mandatory braces reduce maintenance defects when additional statements are later inserted.

**ComplyC Rule:** `FORMAT_BRACE_001`

---

## 4.2 Brace Placement

The default ComplyC beta coding profile uses an opening brace on a new line.

```c
if (condition)
{
    process_data();
}
else
{
    report_error();
}
```

**ComplyC Rule:** `BRACE_STYLE_002`

This is a ComplyC profile decision rather than a universal C-language requirement.

---

## 4.3 One Statement Per Line

**Recommended**

Use one logical statement per line.

Preferred:

```c
initialize_adc();
initialize_pwm();
start_scheduler();
```

Avoid:

```c
initialize_adc(); initialize_pwm(); start_scheduler();
```

---

# 5. Function Design

## 5.1 Keep Functions Focused

**Required by the default ComplyC profile**

A function should perform one clear responsibility.

The default ComplyC profile limits functions to **40 lines**.

When a function becomes excessively large, divide it into smaller logical operations.

**ComplyC Rule:** `FUNC_SIZE_001`

---

## 5.2 Limit Function Parameters

**Required by the default ComplyC profile**

Functions shall have no more than **6 parameters**.

Instead of:

```c
void update_control(
    uint16_t voltage,
    uint16_t current,
    uint16_t speed,
    uint16_t temperature,
    uint16_t torque,
    uint16_t state,
    uint16_t mode,
    uint16_t error);
```

consider grouping strongly related data into an appropriate structure.

**ComplyC Rule:** `FUNC_PARAMS_001`

---

## 5.3 Limit Cyclomatic Complexity

**Required by the default ComplyC profile**

Cyclomatic complexity shall not exceed **10**.

Highly complex functions are more difficult to:

- understand;
- review;
- unit test;
- achieve structural coverage for; and
- safely modify.

**ComplyC Rule:** `FUNC_CC_001`

---

## 5.4 Limit Nesting

**Required by the default ComplyC profile**

Control-flow nesting shall not exceed **4 levels**.

Deeply nested logic should be simplified using techniques such as:

- helper functions;
- early validation;
- state machines; or
- simplified conditional expressions.

**ComplyC Rule:** `FUNC_NESTING_001`

---

## 5.5 Empty Functions

**Required**

Functions shall not contain an unintentionally empty body.

Avoid:

```c
void diagnostic_task(void)
{
}
```

If an intentionally empty implementation is required by an interface, document the reason explicitly.

**ComplyC Rule:** `DEAD_CODE_EMPTY_FUNC_001`

---

# 6. Control Flow

## 6.1 Assignment Inside Conditions

**Required**

Do not place assignments inside conditional expressions.

Avoid:

```c
if (status = read_status())
{
    process_status();
}
```

Prefer:

```c
status = read_status();

if (STATUS_VALID == status)
{
    process_status();
}
```

This prevents accidental confusion between `=` and `==` and makes side effects explicit.

**ComplyC Rule:** `MISRA_LITE_ASSIGN_COND_001`

---

## 6.2 Complete If / Else-If Chains

**Required by the default ComplyC profile**

An `if` / `else if` chain shall terminate with an `else`.

```c
if (STATE_IDLE == state)
{
    handle_idle();
}
else if (STATE_ACTIVE == state)
{
    handle_active();
}
else
{
    handle_invalid_state();
}
```

The final branch provides explicit handling of unexpected states.

**ComplyC Rule:** `CTRL_ELSEIF_001`

---

# 7. Switch Statements

## 7.1 Default Case

**Required**

Every `switch` statement shall contain a `default` label.

```c
switch (state)
{
    case STATE_IDLE:
        handle_idle();
        break;

    case STATE_ACTIVE:
        handle_active();
        break;

    default:
        report_invalid_state();
        break;
}
```

**ComplyC Rule:** `CTRL_SWITCH_DEFAULT_001`

---

## 7.2 Prevent Accidental Fall-Through

**Required**

Each switch case should terminate explicitly unless fall-through is intentional and documented.

```c
case STATE_INIT:
    initialize_system();
    break;
```

Intentional fall-through shall be clearly identified according to the project's accepted convention.

**ComplyC Rule:** `CTRL_SWITCH_FALLTHROUGH_001`

---

# 8. Empty Statements and Blocks

## 8.1 Empty Statements

**Required**

Avoid accidental empty statements.

Dangerous:

```c
if (error_detected);
{
    shutdown_system();
}
```

The semicolon terminates the `if` statement and changes program behavior.

**ComplyC Rule:** `DEAD_CODE_EMPTY_STMT_001`

---

## 8.2 Intentional Empty Blocks

**Required**

If a control block intentionally performs no action, document that decision.

```c
else
{
    /* No action required. */
}
```

**ComplyC Rule:** `CTRL_EMPTY_BLOCK_001`

---

# 9. Unreachable Code

**Required**

Source code shall not contain statements that cannot execute.

Avoid:

```c
return STATUS_OK;

update_diagnostics();
```

The second statement can never execute.

Unreachable code increases maintenance risk and can indicate an implementation error.

**ComplyC Rule:** `DEAD_CODE_UNREACHABLE_001`

---

# 10. Dynamic Memory

## 10.1 Avoid Heap Allocation

**Required by the default ComplyC embedded profile**

Dynamic memory functions are forbidden:

```c
malloc()
calloc()
realloc()
free()
```

Embedded systems frequently require deterministic memory usage and execution behavior.

Prefer:

- statically allocated objects;
- fixed-size buffers;
- compile-time allocation; or
- project-controlled memory pools where explicitly permitted.

**ComplyC Rule:** `SAFETY_DYNAMIC_MEM_001`

---

# 11. Recursion

**Required by the default ComplyC embedded profile**

Recursive function calls are forbidden.

Avoid:

```c
uint32_t factorial(uint32_t value)
{
    if (0U == value)
    {
        return 1U;
    }

    return value * factorial(value - 1U);
}
```

Recursion can make stack usage difficult to bound and is generally undesirable in deterministic embedded systems.

Use bounded iterative implementations instead.

**ComplyC Rule:** `SAFETY_RECURSION_001`

---

# 12. Infinite Loops

**Required by the default ComplyC profile**

Uncontrolled infinite-loop patterns are forbidden.

Examples detected by the current profile include:

```c
while (1)
{
}
```

```c
for (;;)
{
}
```

Embedded systems sometimes legitimately require non-terminating scheduler or main loops. Such architecture-specific cases should therefore be handled through an approved project rule configuration or documented deviation rather than silently introduced.

**ComplyC Rule:** `LOOP_INFINITE_001`

---

# 13. goto

**Required by the default ComplyC profile**

`goto` shall not be used.

Avoid:

```c
if (error)
{
    goto cleanup;
}
```

Prefer structured control flow and focused functions.

**ComplyC Rule:** `FORBIDDEN_GOTO_001`

---

# 14. Unsafe Library Functions

## 14.1 Bounded Data Handling

**Required by the default ComplyC profile**

The default ComplyC profile prohibits selected standard C functions associated with unsafe or ambiguous buffer handling.

Currently checked functions include:

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

For example, avoid:

```c
strcpy(destination, source);
```

Prefer project-approved bounded interfaces where buffer capacity and error behavior are explicit.

**ComplyC Rule:** `SAFETY_FORBIDDEN_API_001`

> The presence of this rule does not mean ComplyC performs complete cybersecurity or memory-safety verification. It detects selected high-confidence source patterns.

---

# 15. Macros

## 15.1 Prefer Constants and Functions Where Appropriate

**Recommended**

Macros should not be used merely to disguise C syntax.

Where appropriate, prefer:

- typed constants;
- `enum` values;
- `static inline` functions; or
- ordinary functions.

---

## 15.2 Parenthesize Macro Expressions

**Recommended**

Avoid:

```c
#define ADD(a, b) a + b
```

Prefer:

```c
#define ADD(a, b) ((a) + (b))
```

This reduces operator-precedence problems.

---

## 15.3 Avoid Macro Side Effects

**Recommended**

Do not design macros that unexpectedly evaluate arguments multiple times.

Expressions such as:

```c
MAX(value++, limit)
```

can produce unexpected behavior depending on the macro implementation.

---

# 16. Variable Initialization

**Recommended**

Initialize variables before use.

Preferred:

```c
uint16_t retry_count = 0U;
bool initialized = false;
```

Uninitialized variables can cause unpredictable behavior and are especially problematic in embedded systems.

A deeper data-flow rule for initialization may be introduced in future ComplyC releases.

---

# 17. Magic Numbers

**Recommended**

Avoid unexplained numeric literals.

Avoid:

```c
if (temperature > 125)
{
    shutdown();
}
```

Prefer:

```c
#define MAX_OPERATING_TEMP_DEG_C    125

if (temperature > MAX_OPERATING_TEMP_DEG_C)
{
    shutdown();
}
```

Named constants communicate intent and make changes easier to review.

Magic-number analysis exists in the ComplyC rule engine, but the corresponding default beta rule may be disabled depending on the distributed configuration.

---

# 18. Header Files

## 18.1 Header Guards

**Recommended**

Header files should prevent multiple inclusion.

```c
#ifndef VOLTAGE_MONITOR_H
#define VOLTAGE_MONITOR_H

void voltage_monitor_init(void);

#endif
```

---

## 18.2 Minimize Header Dependencies

**Recommended**

Include only dependencies required by the interface.

Unnecessary header dependencies increase compilation coupling and make components harder to reuse.

---

# 19. Defensive Embedded C

Embedded software frequently interfaces with hardware, asynchronous events, communication networks, and externally supplied data.

Developers should therefore:

- validate external inputs;
- explicitly handle invalid states;
- check buffer boundaries;
- use fixed-width integer types where appropriate;
- avoid uncontrolled memory allocation;
- avoid ambiguous implicit behavior;
- bound loops and execution where required;
- check function return values where failure is possible; and
- provide deterministic error handling.

These principles complement individual coding rules.

---

# 20. Example

## Poor Implementation

```c
int ProcessData(int x)
{
    char buffer[10];

    if (x = 1)
        strcpy(buffer, "START");

    switch (x)
    {
        case 1:
            start_system();
    }

    return 0;

    log_result();
}
```

Potential issues include:

- incorrect function naming;
- assignment inside a condition;
- missing braces;
- unsafe library function;
- missing switch `default`;
- unreachable code.

---

## Improved Implementation

```c
int process_data(int input_state)
{
    int result = STATUS_OK;

    if (STATE_START == input_state)
    {
        result = process_start_state();
    }
    else
    {
        result = STATUS_INVALID_STATE;
    }

    return result;
}
```

The improved implementation has simpler control flow, explicit state handling, clear naming, and fewer opportunities for unintended behavior.

---

# 21. ComplyC Beta Rule Reference

| Rule ID | Purpose |
|---|---|
| `NAMING_FUNC_001` | Function naming |
| `NAMING_GLOBAL_001` | Global variable naming |
| `NAMING_STATIC_001` | Static variable naming |
| `NAMING_MACRO_001` | Macro naming |
| `NAMING_VAR_003` | Identifier length |
| `NAMING_VAR_004` | Single-letter identifiers |
| `FILE_HEADER_001` | File documentation |
| `FORMAT_BRACE_001` | Mandatory braces |
| `BRACE_STYLE_002` | Brace placement |
| `FUNC_SIZE_001` | Function length |
| `FUNC_CC_001` | Cyclomatic complexity |
| `FUNC_NESTING_001` | Nesting depth |
| `FUNC_PARAMS_001` | Parameter count |
| `DEAD_CODE_EMPTY_FUNC_001` | Empty functions |
| `MISRA_LITE_ASSIGN_COND_001` | Assignment in conditions |
| `CTRL_ELSEIF_001` | Complete conditional chains |
| `CTRL_SWITCH_DEFAULT_001` | Switch default |
| `CTRL_SWITCH_FALLTHROUGH_001` | Switch fall-through |
| `DEAD_CODE_EMPTY_STMT_001` | Empty statements |
| `CTRL_EMPTY_BLOCK_001` | Empty control blocks |
| `DEAD_CODE_UNREACHABLE_001` | Unreachable code |
| `SAFETY_RECURSION_001` | Recursion |
| `SAFETY_DYNAMIC_MEM_001` | Dynamic memory |
| `LOOP_INFINITE_001` | Infinite loops |
| `FORBIDDEN_GOTO_001` | goto |
| `SAFETY_FORBIDDEN_API_001` | Selected unsafe C APIs |

---

# 22. Automated vs. Engineering-Review Guidelines

Not every good coding practice can or should be determined using a simple static rule.

### Automatically Checked

ComplyC beta can automatically evaluate a defined set of naming, formatting, complexity, control-flow, dead-code, and safety-oriented rules.

### Engineering Review

Some practices still require human engineering judgment, including:

- whether a name accurately describes its purpose;
- whether an abstraction is appropriate;
- whether comments explain the important engineering decisions;
- whether module architecture is well layered;
- whether an exception to a coding rule is justified;
- whether concurrency behavior is safe;
- whether hardware interactions are correct; and
- whether the implementation satisfies its software requirements.

Static analysis assists engineering review. It does not replace it.

---

# 23. Relationship to Industry Standards

ComplyC's default guidelines incorporate commonly accepted C and embedded-software practices and contain rules conceptually related to practices found in sources such as:

- MISRA C;
- CERT C;
- established C coding-style guidance;
- embedded-software engineering practice; and
- safety-conscious software development.

References such as **“MISRA-inspired”** identify conceptual relationships only.

ComplyC is **not MISRA-certified**, and successful execution of ComplyC does not establish MISRA, CERT, ISO 26262, ASPICE, cybersecurity, or regulatory compliance.

---

# 24. Using This Guide With ComplyC

A practical workflow is:

```text
Write C Code
     |
     v
Run ComplyC
     |
     v
Review Violations
     |
     v
Correct Code or Document Justification
     |
     v
Re-run Analysis
     |
     v
Peer Review
     |
     v
Commit / Pull Request
```

The objective is not merely to obtain a report containing zero violations.

The objective is to create C software that another engineer can understand, review, test, maintain, and safely modify.

---

# References

1. Carnegie Mellon University-hosted **C Coding Standard**, adapted from earlier C/C++ and NetBSD coding-style guidance.
2. ISO/IEC 9899 — Programming Languages — C.
3. MISRA C — Guidelines for the Use of the C Language in Critical Systems.
4. SEI CERT C Coding Standard.
5. ComplyC Default C Style Rule Configuration.

---

# License and Attribution

This guide is part of the **ComplyC Project**.

The document presents original ComplyC guidance and descriptions of ComplyC's rule set while drawing on established software-engineering principles and publicly available C coding guidance.

Third-party standards and trademarks remain the property of their respective owners.

---

**ComplyC Embedded C Coding Guidelines**  
**Beta Edition — Version 0.9**

*Write clearly. Analyze automatically. Review intelligently.*