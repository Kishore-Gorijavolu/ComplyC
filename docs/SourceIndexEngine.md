# Source Index Engine

## Purpose

The Source Index Engine (SIE) indexes the original C source file once and provides stable locations for the rule engine. This avoids reporting line numbers from GCC-preprocessed code, fake typedef injection, or included header expansion.

## Version

Current engine version: `v0.2.4`.

## Design Contract

1. Index each source file once.
2. Do not rescan files inside lookup methods.
3. Keep lookup methods deterministic and side-effect free.
4. Prefer original source locations for user-facing reports.
5. Fall back safely to GCC source mapping or pycparser coordinates when the source index cannot resolve a location.

## Public API

Rules should use only these stable APIs:

```python
index.find_function(name)
index.find_declaration(name, preferred_line=None)
index.find_static_declaration(name, preferred_line=None)
index.find_global_declaration(name, preferred_line=None)
index.has_macro(name)
index.find_macro(name)
index.find_numeric_literal(raw_token, preferred_line=None)
index.dump_debug(output_path)
```

## Indexed Elements

The engine indexes:

- Function definitions
- Function end lines
- File-scope declarations
- File-scope static declarations
- Local declarations
- Local static declarations
- Macros
- Includes
- Numeric literals from original source text
- Lightweight function calls

## Rule Engine Location Priority

ComplyC report location resolution should use this priority:

1. Source Index Engine
2. GCC `#line` source mapping
3. Raw pycparser coordinate
4. Safe fallback to the scanned file

## Macro Constant Behavior

For magic-number detection, the Source Index Engine checks whether the raw number exists on the original source line.

Example:

```c
#define MAX_SPEED 100u
if (speed > MAX_SPEED)
```

GCC may expose `100u` to pycparser, but the original source line contains `MAX_SPEED`. ComplyC suppresses the magic-number warning in this case.

This still reports correctly:

```c
if (speed > 100u)
```

## Regression Test

Run:

```bash
python tests/test_source_index_engine.py
```

Expected checks include:

- `Tsk_button` resolves to its original source line.
- File-scope static variables resolve correctly.
- Local static variables resolve correctly.
- Macro-expanded constants are not treated as raw magic numbers.
