"""
compiler_extensions.py - Compiler extension sanitizer for ComplyC.

This module normalizes compiler-specific C extensions into pycparser-friendly C
without modifying the user's original source files.

The sanitizer is intentionally conservative: it removes syntax that pycparser
cannot understand while preserving surrounding declarations/functions so the AST
can still be built and source locations remain usable.
"""
from __future__ import annotations

import re
from typing import Iterable


_BALANCED_PREFIXES = (
    "__attribute__",      # GCC: __attribute__((section(".x")))
    "__declspec",         # MSVC/ARM: __declspec(...)
    "__interrupt",        # Some embedded compilers: __interrupt(...)
    "__ISR",              # Microchip-style: __ISR(...)
)

_SIMPLE_KEYWORDS = (
    # GCC / Clang common extension keywords
    "__extension__",
    "__inline__",
    "__inline",
    "__restrict__",
    "__restrict",
    "__volatile__",
    "__volatile",
    "__signed__",
    "__signed",

    # IAR / Keil / ARM / embedded common markers
    "__irq",
    "__fiq",
    "__weak",
    "__root",
    "__ramfunc",
    "__packed",
    "__no_init",
    "__near",
    "__far",
    "__huge",
)


_TYPE_ALIASES = {
    # Common compiler-specific aliases that may appear after preprocessing.
    "__builtin_va_list": "void *",
    "__gnuc_va_list": "void *",
}


def _remove_balanced_call(code: str, keyword: str) -> str:
    """Remove keyword(...) with balanced parentheses, preserving other text."""
    result: list[str] = []
    i = 0
    n = len(code)

    while i < n:
        if code.startswith(keyword, i):
            before_ok = i == 0 or not (code[i - 1].isalnum() or code[i - 1] == "_")
            after_idx = i + len(keyword)
            after_ok = after_idx >= n or not (code[after_idx].isalnum() or code[after_idx] == "_")

            if before_ok and after_ok:
                j = after_idx
                while j < n and code[j].isspace():
                    # Preserve newlines consumed while skipping whitespace.
                    if code[j] == "\n":
                        result.append("\n")
                    j += 1

                if j < n and code[j] == "(":
                    depth = 0
                    while j < n:
                        ch = code[j]
                        if ch == "(":
                            depth += 1
                        elif ch == ")":
                            depth -= 1
                            if depth == 0:
                                j += 1
                                break
                        elif ch == "\n":
                            # Preserve physical line count for coordinate stability.
                            result.append("\n")
                        j += 1
                    i = j
                    continue

        result.append(code[i])
        i += 1

    return "".join(result)


def _remove_balanced_extensions(code: str) -> str:
    for keyword in _BALANCED_PREFIXES:
        code = _remove_balanced_call(code, keyword)
    return code


def _remove_line_pragmas_keep_line_count(code: str) -> str:
    """Blank pycparser-hostile pragma lines while preserving line count."""
    cleaned: list[str] = []
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#pragma") or stripped.startswith("# pragma"):
            cleaned.append("")
        elif stripped.startswith("_Pragma"):
            cleaned.append("")
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def _replace_type_aliases(code: str) -> str:
    for src, dst in _TYPE_ALIASES.items():
        code = re.sub(rf"\b{re.escape(src)}\b", dst, code)
    return code


def _remove_simple_keywords(code: str, keywords: Iterable[str] = _SIMPLE_KEYWORDS) -> str:
    for keyword in keywords:
        code = re.sub(rf"\b{re.escape(keyword)}\b", "", code)
    return code


def _remove_inline_asm_blocks(code: str) -> str:
    """
    Remove simple asm/asm volatile(...) statements and expressions.

    This handles the common preprocessed forms enough to avoid pycparser failures.
    Complex compiler assembly syntax should be skipped by future compiler-specific
    sanitizer plugins rather than interpreted as C.
    """
    for keyword in ("__asm__", "__asm", "asm"):
        code = _remove_balanced_call(code, keyword)
    return code


def sanitize_compiler_extensions(code: str) -> str:
    """
    Convert common embedded/compiler-specific extensions into pycparser-friendly C.

    Supported now:
    - GCC/Clang __attribute__((...)) including nested section strings
    - __extension__, __inline__, __restrict__, __volatile__
    - IAR/Keil/ARM markers such as __irq, __weak, __packed, __root, __ramfunc
    - Basic __declspec(...), __interrupt(...), __ISR(...)
    - Basic pragma/inline asm removal

    The original source files are not changed. This only cleans the temporary text
    sent to pycparser.
    """
    code = _remove_line_pragmas_keep_line_count(code)
    code = _remove_balanced_extensions(code)
    code = _remove_inline_asm_blocks(code)
    code = _replace_type_aliases(code)
    code = _remove_simple_keywords(code)

    # Remove leftover double-underscore implementation markers that commonly
    # appear in system/fake headers and break pycparser. Keep this after the
    # targeted cleaners so attributes do not leave broken punctuation behind.
    code = re.sub(r"\b__\w+\b", "", code)

    # Clean up common broken fragments left by removed compiler constructs.
    code = re.sub(r"^\s*\(\s*\)\s*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"^\s*\(\s*$", "", code, flags=re.MULTILINE)
    return code
