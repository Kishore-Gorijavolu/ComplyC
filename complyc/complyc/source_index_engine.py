"""
source_index_engine.py - Stable Original Source Index Engine for ComplyC.

Source Index Engine (SIE) v0.2.4
---------------------------------
The rule engine should not trust pycparser/GCC preprocessed coordinates for
user-facing report locations. This module indexes the ORIGINAL source file once
and exposes fast, deterministic lookups for symbols and literals.

Design rules:
    1. Index a file once; never rescan inside find_* methods.
    2. Keep lookups deterministic and side-effect free.
    3. Use line-oriented parsing only; avoid large DOTALL regex patterns.
    4. Fail safe. If a construct is too complex, skip it and allow rule_engine
       to fall back to GCC line mapping / raw pycparser coordinates.

This is intentionally a lightweight source indexer, not a full C parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import re
from bisect import bisect_left
from typing import Dict, Iterable, List, Optional, Tuple

SIE_VERSION = "0.2.4"


# ============================================================
# Data model
# ============================================================

@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: int = 1


@dataclass
class FunctionSymbol:
    name: str
    location: SourceLocation
    end_line: Optional[int] = None
    calls: List[Tuple[str, SourceLocation]] = field(default_factory=list)


@dataclass
class DeclarationSymbol:
    name: str
    location: SourceLocation
    storage: Tuple[str, ...] = field(default_factory=tuple)
    type_hint: str = ""
    scope: str = "global"  # global, static_global, local, parameter, unknown

    @property
    def is_static(self) -> bool:
        return "static" in self.storage

    @property
    def is_global_scope(self) -> bool:
        return self.scope in ("global", "static_global")


@dataclass
class MacroSymbol:
    name: str
    location: SourceLocation
    body: str = ""
    function_like: bool = False


@dataclass
class IncludeSymbol:
    target: str
    location: SourceLocation
    system: bool = False


@dataclass
class NumericLiteral:
    raw: str
    location: SourceLocation
    canonical: str


@dataclass
class SourceIndex:
    file_path: str
    line_count: int = 0
    functions: Dict[str, FunctionSymbol] = field(default_factory=dict)
    declarations: Dict[str, List[DeclarationSymbol]] = field(default_factory=dict)
    macros: Dict[str, MacroSymbol] = field(default_factory=dict)
    includes: List[IncludeSymbol] = field(default_factory=list)
    numeric_literals: List[NumericLiteral] = field(default_factory=list)

    # Built after numeric indexing. canonical token -> list of literals in source order.
    _literal_by_canonical: Dict[str, List[NumericLiteral]] = field(default_factory=dict, repr=False)
    _decl_names: set = field(default_factory=set, repr=False)

    def finalize(self) -> None:
        self._literal_by_canonical.clear()
        for lit in self.numeric_literals:
            self._literal_by_canonical.setdefault(lit.canonical, []).append(lit)
        self._decl_names = set(self.declarations.keys())

    # ---- frozen public API for rule_engine.py ----

    def find_function(self, name: Optional[str]) -> Optional[SourceLocation]:
        if not name:
            return None
        item = self.functions.get(name)
        return item.location if item else None

    def find_function_symbol(self, name: Optional[str]) -> Optional[FunctionSymbol]:
        return self.functions.get(name) if name else None

    def find_declaration(
        self,
        name: Optional[str],
        preferred_line: Optional[int] = None,
        static_only: Optional[bool] = None,
        global_only: bool = False,
    ) -> Optional[SourceLocation]:
        decl = self.find_declaration_symbol(
            name,
            preferred_line=preferred_line,
            static_only=static_only,
            global_only=global_only,
        )
        return decl.location if decl else None

    def find_declaration_symbol(
        self,
        name: Optional[str],
        preferred_line: Optional[int] = None,
        static_only: Optional[bool] = None,
        global_only: bool = False,
    ) -> Optional[DeclarationSymbol]:
        if not name:
            return None
        items = self.declarations.get(name) or []
        if static_only is not None:
            items = [d for d in items if d.is_static == static_only]
        if global_only:
            items = [d for d in items if d.is_global_scope]
        if not items:
            return None
        if preferred_line is None:
            return items[0]
        return min(items, key=lambda d: abs(d.location.line - int(preferred_line)))

    def find_static_declaration(self, name: Optional[str], preferred_line: Optional[int] = None) -> Optional[SourceLocation]:
        return self.find_declaration(name, preferred_line=preferred_line, static_only=True)

    def find_global_declaration(self, name: Optional[str], preferred_line: Optional[int] = None) -> Optional[SourceLocation]:
        return self.find_declaration(name, preferred_line=preferred_line, global_only=True)

    def has_original_declaration(self, name: Optional[str]) -> bool:
        return bool(name and name in self._decl_names)

    def has_macro(self, name: Optional[str]) -> bool:
        return bool(name and name in self.macros)

    def find_macro(self, name: Optional[str]) -> Optional[SourceLocation]:
        if not name:
            return None
        item = self.macros.get(name)
        return item.location if item else None

    def find_numeric_literal(self, raw_token: str, preferred_line: Optional[int] = None) -> Optional[SourceLocation]:
        """
        Deterministic literal lookup.

        If preferred_line is supplied, only exact same-line matches are returned.
        This is important for macro suppression: if GCC expanded MAX_SPEED to 100,
        the mapped original line contains MAX_SPEED, not raw 100, so this returns
        None and the magic-number rule suppresses the false violation.

        If preferred_line is not supplied, return the first literal in source order
        for compatibility with builtin/demo parsing.
        """
        wanted = canonical_numeric_token(raw_token)
        if wanted is None:
            return None
        items = self._literal_by_canonical.get(wanted) or []
        if not items:
            return None
        if preferred_line is None:
            return items[0].location
        for lit in items:
            if lit.location.line == int(preferred_line):
                return lit.location
        return None

    def next_numeric_literal(self, raw_token: str) -> Optional[SourceLocation]:
        """Backward-compatible alias. Prefer find_numeric_literal()."""
        return self.find_numeric_literal(raw_token)

    def dump_debug(self, output_path: str) -> None:
        payload = {
            "version": SIE_VERSION,
            "file_path": self.file_path,
            "line_count": self.line_count,
            "functions": {
                name: {
                    "line": sym.location.line,
                    "column": sym.location.column,
                    "end_line": sym.end_line,
                    "calls": [
                        {"name": call, "line": loc.line, "column": loc.column}
                        for call, loc in sym.calls
                    ],
                }
                for name, sym in sorted(self.functions.items())
            },
            "declarations": {
                name: [
                    {
                        "line": d.location.line,
                        "column": d.location.column,
                        "scope": d.scope,
                        "storage": list(d.storage),
                        "type_hint": d.type_hint,
                    }
                    for d in decls
                ]
                for name, decls in sorted(self.declarations.items())
            },
            "macros": {
                name: {"line": m.location.line, "column": m.location.column, "function_like": m.function_like, "body": m.body}
                for name, m in sorted(self.macros.items())
            },
            "includes": [
                {"target": inc.target, "line": inc.location.line, "system": inc.system}
                for inc in self.includes
            ],
            "numeric_literals": [
                {"raw": lit.raw, "canonical": lit.canonical, "line": lit.location.line, "column": lit.location.column}
                for lit in self.numeric_literals
            ],
        }
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ============================================================
# Cache
# ============================================================

_CACHE: Dict[Tuple[str, float, int], SourceIndex] = {}
_MAX_CACHE_ENTRIES = 128


def clear_source_index_cache() -> None:
    _CACHE.clear()


def get_source_index(file_path: str) -> SourceIndex:
    """Cached entry point used by rule_engine.py."""
    path = os.path.abspath(file_path)
    try:
        stat = os.stat(path)
        key = (path, stat.st_mtime, stat.st_size)
    except OSError:
        key = (path, 0.0, 0)

    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    index = build_source_index(path)
    if len(_CACHE) >= _MAX_CACHE_ENTRIES:
        _CACHE.clear()
    _CACHE[key] = index
    return index


# ============================================================
# Build pipeline
# ============================================================


def build_source_index(file_path: str) -> SourceIndex:
    path = os.path.abspath(file_path)
    try:
        original_text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return SourceIndex(file_path=path)

    stripped_text = strip_comments_preserve_lines(original_text)
    lines = stripped_text.splitlines()

    index = SourceIndex(file_path=path, line_count=len(lines))
    _index_preprocessor(index, path, lines)
    _index_functions(index, path, lines)
    _index_declarations(index, path, lines)
    _index_calls(index, path, lines)
    _index_numeric_literals(index, path, lines)
    index.finalize()
    return index


# ============================================================
# Comment stripping / lexical helpers
# ============================================================


def strip_comments_preserve_lines(text: str) -> str:
    """Remove C comments while preserving line numbers and approximate columns."""
    result: List[str] = []
    i = 0
    n = len(text)
    in_block = False
    in_line = False
    in_string = False
    in_char = False
    escape = False

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if in_line:
            if ch == "\n":
                in_line = False
                result.append(ch)
            else:
                result.append(" ")
            i += 1
            continue

        if in_block:
            if ch == "*" and nxt == "/":
                result.extend("  ")
                i += 2
                in_block = False
            else:
                result.append("\n" if ch == "\n" else " ")
                i += 1
            continue

        if in_string or in_char:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif in_string and ch == '"':
                in_string = False
            elif in_char and ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            result.extend("  ")
            i += 2
            in_line = True
            continue
        if ch == "/" and nxt == "*":
            result.extend("  ")
            i += 2
            in_block = True
            continue
        if ch == '"':
            in_string = True
        elif ch == "'":
            in_char = True
        result.append(ch)
        i += 1

    return "".join(result)


def _brace_delta(line: str) -> int:
    return line.count("{") - line.count("}")


def _paren_delta(line: str) -> int:
    return line.count("(") - line.count(")")


def _split_top_level_commas(text: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth_paren = depth_brace = depth_bracket = 0
    for ch in text:
        if ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren > 0:
            depth_paren -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}" and depth_brace > 0:
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]" and depth_bracket > 0:
            depth_bracket -= 1
        if ch == "," and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _left_of_initializer(text: str) -> str:
    depth_paren = depth_brace = depth_bracket = 0
    out: List[str] = []
    for ch in text:
        if ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren > 0:
            depth_paren -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}" and depth_brace > 0:
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]" and depth_bracket > 0:
            depth_bracket -= 1
        elif ch == "=" and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
            break
        out.append(ch)
    return "".join(out)


def _statement_has_top_level_semicolon(line: str) -> bool:
    depth_paren = depth_brace = depth_bracket = 0
    for ch in line:
        if ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren > 0:
            depth_paren -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}" and depth_brace > 0:
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]" and depth_bracket > 0:
            depth_bracket -= 1
        elif ch == ";" and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
            return True
    return False


def _first_statement(text: str) -> str:
    depth_paren = depth_brace = depth_bracket = 0
    out: List[str] = []
    for ch in text:
        if ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren > 0:
            depth_paren -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}" and depth_brace > 0:
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]" and depth_bracket > 0:
            depth_bracket -= 1
        elif ch == ";" and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
            break
        out.append(ch)
    return "".join(out)


# ============================================================
# Indexers
# ============================================================


def _index_preprocessor(index: SourceIndex, path: str, lines: List[str]) -> None:
    include_re = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]')
    define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)(\s*\([^)]*\))?\s*(.*)$')

    for lineno, line in enumerate(lines, start=1):
        inc = include_re.match(line)
        if inc:
            index.includes.append(
                IncludeSymbol(
                    target=inc.group(2),
                    location=SourceLocation(path, lineno, max(line.find("#"), 0) + 1),
                    system=inc.group(1) == "<",
                )
            )
            continue

        macro = define_re.match(line)
        if macro:
            name = macro.group(1)
            index.macros[name] = MacroSymbol(
                name=name,
                location=SourceLocation(path, lineno, line.find(name) + 1),
                function_like=bool(macro.group(2)),
                body=(macro.group(3) or "").strip(),
            )


def _index_functions(index: SourceIndex, path: str, lines: List[str]) -> None:
    control_words = {"if", "for", "while", "switch", "return", "sizeof", "case", "do"}
    qualifiers = r"(?:static\s+|extern\s+|inline\s+|const\s+|volatile\s+|register\s+|auto\s+|signed\s+|unsigned\s+|short\s+|long\s+|struct\s+|union\s+|enum\s+|[A-Za-z_]\w*\s+|\*\s*)+"
    func_re = re.compile(r"^\s*" + qualifiers + r"(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{")

    pending: List[Tuple[int, str]] = []
    paren_depth = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            pending.clear()
            paren_depth = 0
            continue

        one = func_re.match(line)
        if one:
            name = one.group("name")
            if name not in control_words and name not in index.functions:
                index.functions[name] = FunctionSymbol(name=name, location=SourceLocation(path, lineno, line.find(name) + 1))
            pending.clear()
            paren_depth = 0
            continue

        # Multiline function signature. Avoid control statements and prototypes.
        first_word = stripped.split("(", 1)[0].strip().split()[-1] if "(" in stripped and stripped.split("(", 1)[0].strip().split() else ""
        if not pending and "(" in stripped and ";" not in stripped and first_word not in control_words:
            pending = [(lineno, line)]
            paren_depth = _paren_delta(line)
            if "{" in line and paren_depth <= 0:
                _finish_pending_function(index, path, pending, control_words)
                pending.clear()
                paren_depth = 0
            continue

        if pending:
            pending.append((lineno, line))
            paren_depth += _paren_delta(line)
            combined = " ".join(x[1].strip() for x in pending)
            if ";" in combined:
                pending.clear()
                paren_depth = 0
                continue
            if "{" in combined and paren_depth <= 0:
                _finish_pending_function(index, path, pending, control_words)
                pending.clear()
                paren_depth = 0

    for func in index.functions.values():
        func.end_line = _find_function_end(lines, func.location.line)


def _finish_pending_function(index: SourceIndex, path: str, pending: List[Tuple[int, str]], control_words: set) -> None:
    combined = " ".join(x[1].strip() for x in pending)
    m = re.search(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{", combined)
    if not m:
        return
    name = m.group(1)
    if name in control_words or name in index.functions:
        return
    name_line, name_col = pending[0][0], 1
    for lno, txt in pending:
        pos = txt.find(name)
        if pos >= 0:
            name_line, name_col = lno, pos + 1
            break
    index.functions[name] = FunctionSymbol(name=name, location=SourceLocation(path, name_line, name_col))


def _find_function_end(lines: List[str], start_line: int) -> Optional[int]:
    depth = 0
    seen_open = False
    for idx in range(start_line - 1, len(lines)):
        for ch in lines[idx]:
            if ch == "{":
                depth += 1
                seen_open = True
            elif ch == "}":
                depth -= 1
                if seen_open and depth <= 0:
                    return idx + 1
    return None


def _scope_at_line(index: SourceIndex, line: int) -> str:
    for func in index.functions.values():
        if func.location.line < line and func.end_line and line <= func.end_line:
            return "local"
    return "global"


def _active_function_at_line(index: SourceIndex, line: int) -> Optional[FunctionSymbol]:
    for func in index.functions.values():
        if func.location.line < line and func.end_line and line <= func.end_line:
            return func
    return None


def _index_calls(index: SourceIndex, path: str, lines: List[str]) -> None:
    control_words = {"if", "for", "while", "switch", "return", "sizeof", "case", "do"}
    for lineno, line in enumerate(lines, start=1):
        func = _active_function_at_line(index, lineno)
        if not func:
            continue
        for match in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", line):
            name = match.group(1)
            if name not in control_words and name != func.name:
                func.calls.append((name, SourceLocation(path, lineno, match.start(1) + 1)))


def _index_declarations(index: SourceIndex, path: str, lines: List[str]) -> None:
    keywords = {
        "if", "for", "while", "switch", "return", "sizeof", "case", "else", "do",
        "typedef", "struct", "union", "enum", "const", "volatile", "static", "extern",
        "register", "auto", "signed", "unsigned", "short", "long", "void", "char",
        "int", "float", "double", "bool", "inline", "restrict",
    }
    control_starts = ("if", "for", "while", "switch", "return", "case", "else", "do", "sizeof")
    type_start_re = re.compile(
        r"^\s*(?:(?:static|const|volatile|extern|register|auto|inline|signed|unsigned|short|long)\s+)*"
        r"(?:(?:struct|union|enum)\s+)?[A-Za-z_]\w*"
    )

    logical_stmt = ""
    stmt_start_line = 1
    brace_depth = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Skip block openers/function signatures so local declarations inside
        # functions are not swallowed into a giant function-body statement.
        if not logical_stmt and "{" in stripped and ";" not in stripped:
            continue
        if logical_stmt and stripped == "{" and ";" not in stripped:
            logical_stmt = ""
            continue

        if not logical_stmt:
            stmt_start_line = lineno
        logical_stmt += line + "\n"

        # Do not terminate on semicolons inside initializer braces.
        if not _statement_has_top_level_semicolon(logical_stmt):
            # If this was a function/control signature that opened a block, drop it.
            if "{" in logical_stmt and ";" not in logical_stmt:
                logical_stmt = ""
            continue

        statement = _first_statement(logical_stmt)
        logical_stmt = ""

        stmt_strip = statement.strip()
        if not stmt_strip:
            continue
        first_token = stmt_strip.split(None, 1)[0]
        if first_token in control_starts:
            continue
        left = _left_of_initializer(statement)
        # Skip prototypes/function calls/casts in declarator area.
        if "(" in left and ")" in left:
            continue
        if not type_start_re.match(statement):
            continue

        scope = _scope_at_line(index, stmt_start_line)
        storage_tokens = tuple(re.findall(r"\b(static|extern|register|auto|const|volatile)\b", statement))
        if "static" in storage_tokens and scope == "global":
            scope = "static_global"

        declarator_parts = _split_top_level_commas(statement)
        for part_index, part in enumerate(declarator_parts):
            candidate = _left_of_initializer(part)
            candidate = re.sub(r"\[[^\]]*\]", "", candidate)
            candidate = candidate.replace("*", " ").strip()
            ids = re.findall(r"\b[A-Za-z_]\w*\b", candidate)
            if not ids:
                continue
            name = ids[-1]
            if name in keywords:
                continue
            if part_index == 0 and len(ids) < 2:
                continue
            if name in index.functions:
                continue

            loc_line, loc_col = _locate_name_in_statement(statement, stmt_start_line, name)
            type_hint = " ".join(ids[:-1])
            index.declarations.setdefault(name, []).append(
                DeclarationSymbol(
                    name=name,
                    location=SourceLocation(path, loc_line, loc_col),
                    storage=storage_tokens,
                    type_hint=type_hint,
                    scope=scope,
                )
            )


def _locate_name_in_statement(statement: str, stmt_start_line: int, name: str) -> Tuple[int, int]:
    word_re = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])")
    for offset, txt in enumerate(statement.splitlines()):
        m = word_re.search(txt)
        if m:
            return stmt_start_line + offset, m.start() + 1
    return stmt_start_line, 1


def _index_numeric_literals(index: SourceIndex, path: str, lines: List[str]) -> None:
    number_re = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"(?:0[xX][0-9A-Fa-f]+[uUlL]*|"
        r"\d+\.\d*(?:[eE][+-]?\d+)?[fFlL]?|"
        r"\d+(?:[eE][+-]?\d+)[fFlL]?|"
        r"\d+[uUlL]*)"
        r"(?![A-Za-z0-9_])"
    )

    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("#"):
            continue
        for m in number_re.finditer(line):
            raw = m.group(0)
            canonical = canonical_numeric_token(raw)
            if canonical is None:
                continue
            index.numeric_literals.append(
                NumericLiteral(raw=raw, canonical=canonical, location=SourceLocation(path, lineno, m.start() + 1))
            )


def canonical_numeric_token(token: str) -> Optional[str]:
    if token is None:
        return None
    s = str(token).strip()
    if not s:
        return None
    s = re.sub(r"[uUlLfF]+$", "", s)
    try:
        if s.lower().startswith("0x"):
            return str(int(s, 16))
        if re.match(r"^0[0-7]+$", s):
            return str(int(s, 8))
        if any(c in s for c in ".eE"):
            return str(float(s))
        return str(int(s, 10))
    except ValueError:
        return s


# ============================================================
# Backward-compatible names for current ComplyC integration
# ============================================================

SourceCallGraph = SourceIndex
FunctionRecord = FunctionSymbol
get_source_callgraph = get_source_index
build_source_callgraph = build_source_index
