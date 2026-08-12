# ComplyC Security Rule Pack v1

## Objective

Security Rule Pack v1 adds conservative, explainable AST checks for C and embedded-C projects. The pack intentionally prioritizes high-confidence findings over broad heuristic coverage. It is a security review aid, not a replacement for threat modeling, compiler hardening, fuzzing, penetration testing, or interprocedural taint/data-flow analysis.

## Rule Catalog

| Rule ID | Security concern | CWE | Severity | Detection strategy |
|---|---|---:|---|---|
| SEC_INPUT_GETS_001 | Use of `gets()` | CWE-242 | Critical | Exact forbidden call |
| SEC_STRING_COPY_002 | Unbounded `strcpy`/`strcat` family | CWE-120 | Critical | Exact forbidden call |
| SEC_FORMAT_WRITE_003 | Unbounded `sprintf`/`vsprintf` | CWE-120 | Critical | Exact forbidden call |
| SEC_FORMAT_STRING_004 | Non-literal format string | CWE-134 | Critical | API-specific format-argument inspection |
| SEC_SCANF_WIDTH_005 | `%s`/`%[` without field width | CWE-120 | Critical | Literal format parsing |
| SEC_COMMAND_EXEC_006 | Shell command execution APIs | CWE-78 | Critical | Exact forbidden call |
| SEC_TEMP_FILE_007 | Race-prone temporary-file APIs | CWE-377 | Major | Exact forbidden call |
| SEC_WEAK_RANDOM_008 | Weak PRNG APIs | CWE-338 | Major | Exact forbidden call |
| SEC_OBSOLETE_CRYPTO_009 | MD5, SHA-1, or DES entry points | CWE-327 | Major | Exact forbidden call |
| SEC_HARDCODED_SECRET_010 | Secret-like variable initialized with a literal | CWE-798 | Critical | Identifier + initializer inspection |
| SEC_ARRAY_BOUNDS_011 | Constant index outside a declared constant array | CWE-125 / CWE-787 | Critical | Declaration and array-reference analysis |
| SEC_DIV_ZERO_012 | Constant division/modulo by zero | CWE-369 | Critical | Binary-expression inspection |
| SEC_INVALID_SHIFT_013 | Negative/out-of-range shift or negative left operand | CWE-758 | Major | Binary-expression inspection |
| SEC_ALLOC_OVERFLOW_014 | Allocation size computed by unchecked multiplication | CWE-190 / CWE-131 | Major | Allocation-call argument pattern |

## Examples

### Non-literal format string

Bad:

```c
printf(user_text);
```

Good:

```c
printf("%s", user_text);
```

### Bounded string input

Bad:

```c
scanf("%s", buffer);
```

Good for a 16-byte destination:

```c
scanf("%15s", buffer);
```

### Allocation multiplication

Bad:

```c
items = malloc(count * sizeof(*items));
```

Preferred:

```c
if (count <= (SIZE_MAX / sizeof(*items)))
{
    items = malloc(count * sizeof(*items));
}
```

## Test Assets

- `ComplyC/examples/security_pack_v1_bad.c`: triggers the applicable v1 rules.
- `ComplyC/examples/security_pack_v1_good.c`: demonstrates accepted bounded output and literal formatting.
- `ComplyC/tests/security/test_security_pack_v1.py`: verifies expected detection and zero security findings for the good fixture.

Run from the `ComplyC` directory:

```bash
PYTHONPATH=. pytest -q tests/security/test_security_pack_v1.py
```

## HTML Security Summary

The HTML report contains a dedicated **Security Summary** before the general rule summary. It reports the security review status, critical/major counts, findings grouped by category, CWE mappings, and Category/CWE columns in the per-file table.

## Known v1 Boundaries

The following are intentionally deferred because reliable detection requires symbol resolution, control-flow, taint, range, or interprocedural data-flow analysis:

- User-controlled data reaching command, file, memory, or format sinks.
- General runtime array bounds.
- Null dereference and lifetime defects.
- Use-after-free and double-free across branches/functions.
- Integer truncation and signedness defects requiring type/range propagation.
- Authentication, authorization, cryptographic protocol, and secure-boot design defects.

## Recommended v1.1 Direction

1. Load the security pack as a separately selectable YAML profile.
2. Add confidence and remediation fields to the report schema.
3. Introduce call-site return-value checks for selected security APIs.
4. Add lightweight intra-procedural taint propagation.
5. Support configurable platform type widths for shift and overflow rules.
