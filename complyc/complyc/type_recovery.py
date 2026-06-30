"""
type_recovery.py - Lightweight Type Recovery Engine for ComplyC.

Purpose
-------
pycparser needs project/vendor typedef names to be known before it can parse
real embedded C. Production projects frequently use generated typedefs,
compiler headers, HAL structures, enum aliases, and project-specific state
machines. When those declarations are unavailable or sanitized out, pycparser
can fail with errors such as:

    Missing type in declaration
    before: status

This module infers probable missing type names from the sanitized source text
and injects harmless placeholder typedefs ahead of the temporary text sent to
pycparser. The original source file is never modified.

Design rules
------------
* Conservative and syntax-focused: this is for parsing continuity, not semantic
  correctness.
* One-shot inference: no recursive file scanning and no dependency traversal.
* Line-offset aware: callers receive the number of injected lines so source
  mapping can compensate in GCC mode.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple


@dataclass(frozen=True)
class TypeRecoveryResult:
    code: str
    recovered_types: Tuple[str, ...]
    injected_line_count: int


# Standard C / common embedded scalar names that should not be recovered.
_BUILTIN_TYPE_WORDS: Set[str] = {
    "void", "char", "short", "int", "long", "float", "double", "signed", "unsigned",
    "_Bool", "bool", "size_t", "ssize_t", "ptrdiff_t", "uintptr_t", "intptr_t",
    "int8_t", "uint8_t", "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t",
    "sint8", "uint8", "sint16", "uint16", "sint32", "uint32", "float32", "float64",
    "boolean", "TRUE", "FALSE",
}

_STORAGE_AND_QUALIFIERS: Set[str] = {
    "static", "extern", "register", "auto", "const", "volatile", "restrict",
    "inline", "typedef", "signed", "unsigned", "short", "long", "struct", "union", "enum",
}

_CONTROL_WORDS: Set[str] = {
    "if", "else", "for", "while", "switch", "case", "default", "do", "return",
    "break", "continue", "goto", "sizeof",
}

_COMMON_NON_TYPES: Set[str] = {
    "NULL", "true", "false",
}

_DECL_START_RE = re.compile(
    r"^\s*(?:(?:static|extern|register|auto|const|volatile|inline)\s+)*"
    r"(?P<type>[A-Za-z_]\w*)\s*"
    r"(?P<ptr>\*+\s*)?"
    r"(?P<name>[A-Za-z_]\w*)\s*(?:[=;,\[\)])"
)

_FUNC_DEF_OR_PROTO_RE = re.compile(
    r"^\s*(?:(?:static|extern|inline|const|volatile)\s+)*"
    r"(?P<type>[A-Za-z_]\w*)\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\("
)

_PARAM_RE = re.compile(
    r"(?:^|[,\(])\s*(?:(?:const|volatile|register)\s+)*"
    r"(?P<type>[A-Za-z_]\w*)\s*(?:\*+\s*)?"
    r"(?P<name>[A-Za-z_]\w*)\s*(?=,|\)|\[)"
)

_CAST_RE = re.compile(r"\(\s*(?P<type>[A-Za-z_]\w*)\s*(?:\*\s*)?\)")

_TYPEDEF_NAME_RE = re.compile(r"\btypedef\b[^;{}]*\b(?P<name>[A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*;", re.DOTALL)
_TYPEDEF_COMPOSITE_RE = re.compile(r"\btypedef\s+(?:struct|union|enum)\b.*?\}\s*(?P<name>[A-Za-z_]\w*)\s*;", re.DOTALL)
_STRUCT_TAG_RE = re.compile(r"\b(?:struct|union|enum)\s+(?P<name>[A-Za-z_]\w*)")


# Identifiers with these shapes are usually symbols/macros/functions, not types.
def _looks_like_type_name(name: str) -> bool:
    if not name:
        return False
    if name in _BUILTIN_TYPE_WORDS or name in _STORAGE_AND_QUALIFIERS:
        return False
    if name in _CONTROL_WORDS or name in _COMMON_NON_TYPES:
        return False
    if name.startswith("__"):
        return False

    # Common embedded type styles:
    #   NVM_states, sleep_type, SysTick_Type, DL_FLASHCTL_COMMAND_STATUS,
    #   l_irqmask, ADC_Result_t, FooHandle
    if name.endswith(("_t", "_T", "_type", "_Type", "_TYPE", "_states", "_States", "_STATUS", "Status")):
        return True
    if "_" in name and any(ch.isupper() for ch in name):
        return True
    if name and name[0].isupper():
        return True
    if name.startswith(("l_", "L_")):
        return True
    return False


def _strip_comments_for_inference(code: str) -> str:
    # Preserve newlines to keep line-oriented heuristics readable.
    code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), code, flags=re.DOTALL)
    return code


def _existing_typedef_names(code: str) -> Set[str]:
    names: Set[str] = set()
    for m in _TYPEDEF_NAME_RE.finditer(code):
        names.add(m.group("name"))
    for m in _TYPEDEF_COMPOSITE_RE.finditer(code):
        names.add(m.group("name"))
    return names


def _composite_tags(code: str) -> Set[str]:
    return {m.group("name") for m in _STRUCT_TAG_RE.finditer(code)}


def infer_missing_type_names(code: str) -> List[str]:
    """Infer probable missing typedef names from sanitized C text."""
    scan = _strip_comments_for_inference(code)
    existing = _existing_typedef_names(scan)
    tags = _composite_tags(scan)
    candidates: Set[str] = set()

    # Line-oriented declaration/function heuristics. Avoid expensive DOTALL patterns.
    for raw_line in scan.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("typedef ", "struct ", "union ", "enum ")):
            continue
        if line.startswith(tuple(word + " " for word in _CONTROL_WORDS)):
            continue

        # Variable declaration at block or file scope.
        m = _DECL_START_RE.match(line)
        if m:
            typ = m.group("type")
            name = m.group("name")
            if typ != name and _looks_like_type_name(typ):
                candidates.add(typ)

        # Function return types, including prototypes and definitions. Only then
        # inspect parameters. Do not scan arbitrary function calls, because calls
        # like Foo(BAR) would otherwise make BAR look like a type.
        m = _FUNC_DEF_OR_PROTO_RE.match(line)
        if m:
            typ = m.group("type")
            name = m.group("name")
            if typ != name and _looks_like_type_name(typ):
                candidates.add(typ)

            params_start = line.find("(")
            params_end = line.rfind(")")
            if params_start != -1 and params_end > params_start:
                params = line[params_start:params_end + 1]
                for pm in _PARAM_RE.finditer(params):
                    ptyp = pm.group("type")
                    pname = pm.group("name")
                    if ptyp != pname and _looks_like_type_name(ptyp):
                        candidates.add(ptyp)

        # Cast inference intentionally disabled for now. In embedded code,
        # parenthesized expressions in conditions often look like casts to a
        # regex, e.g. (NVM_write_state != NVM_IDLE). Declaration/function
        # inference is safer and covers the real pycparser typedef failures.

    # Do not inject names already typedef'd or composite tags that are referenced as
    # 'struct Foo'. Bare 'Foo' still needs a typedef and will remain a candidate.
    candidates -= existing
    candidates -= _BUILTIN_TYPE_WORDS
    candidates -= _STORAGE_AND_QUALIFIERS
    candidates -= _CONTROL_WORDS
    candidates -= _COMMON_NON_TYPES

    return sorted(candidates)


def build_recovery_typedefs(type_names: Iterable[str]) -> str:
    lines: List[str] = []
    for name in sorted(set(type_names)):
        if not _looks_like_type_name(name):
            continue
        # Use int as a neutral scalar placeholder. pycparser only needs the token
        # to be recognized as a typedef-name; semantic width is irrelevant here.
        lines.append(f"typedef int {name};")
    return "\n".join(lines)


def apply_type_recovery(code: str) -> TypeRecoveryResult:
    """
    Inject placeholder typedefs for missing project/vendor types.

    Returns the modified code and the number of injected physical lines. The
    caller should subtract this offset when mapping pycparser coordinates back
    to preprocessed/original source lines.
    """
    recovered = tuple(infer_missing_type_names(code))
    typedef_block = build_recovery_typedefs(recovered)
    if not typedef_block:
        return TypeRecoveryResult(code=code, recovered_types=(), injected_line_count=0)

    injected = typedef_block + "\n"
    return TypeRecoveryResult(
        code=injected + code,
        recovered_types=recovered,
        injected_line_count=injected.count("\n"),
    )
