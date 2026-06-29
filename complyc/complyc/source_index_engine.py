"""
source_index_engine.py - Original Source Index Engine for ComplyC.

Purpose
-------
pycparser coordinates can drift when GCC preprocessing expands headers, macros,
or fake typedefs. This engine indexes the ORIGINAL source file and provides stable
user-facing locations for rules and reports.

Use this module as the authority for report locations:
    - function definitions
    - global/static/local declarations
    - numeric literals from original code only
    - function calls / lightweight call graph
    - includes and macros

This is intentionally lightweight and dependency-free. It is not a full C parser;
it is a robust source indexer used to correct/report locations after AST analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple


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


@dataclass
class MacroSymbol:
    name: str
    location: SourceLocation
    body: str = ""


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
    functions: Dict[str, FunctionSymbol] = field(default_factory=dict)
    declarations: Dict[str, List[DeclarationSymbol]] = field(default_factory=dict)
    macros: Dict[str, MacroSymbol] = field(default_factory=dict)
    includes: List[IncludeSymbol] = field(default_factory=list)
    numeric_literals: List[NumericLiteral] = field(default_factory=list)

    _literal_cursor: int = 0

    def find_function(self, name: Optional[str]) -> Optional[SourceLocation]:
        if not name:
            return None
        item = self.functions.get(name)
        return item.location if item else None

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
        items = list(self.declarations.get(name) or [])
        if static_only is not None:
            items = [d for d in items if d.is_static == static_only]
        if global_only:
            items = [d for d in items if d.scope in ("global", "static_global")]
        if not items:
            return None
        if preferred_line is None:
            return items[0]
        return min(items, key=lambda d: abs(d.location.line - int(preferred_line)))

    def has_original_declaration(self, name: Optional[str]) -> bool:
        return bool(name and self.declarations.get(name))

    def find_macro(self, name: Optional[str]) -> Optional[SourceLocation]:
        if not name:
            return None
        item = self.macros.get(name)
        return item.location if item else None

    def next_numeric_literal(self, raw_token: str) -> Optional[SourceLocation]:
        """
        Return the next matching numeric literal from original source text.

        This intentionally avoids macro-expanded numbers. Example:
            #define MAX_SPEED 100
            if (speed > MAX_SPEED)

        pycparser may see 100, but the original source line does not contain raw
        100 at the usage site, so no magic-number location is returned.
        """
        wanted = canonical_numeric_token(raw_token)
        if wanted is None:
            return None

        for idx in range(self._literal_cursor, len(self.numeric_literals)):
            lit = self.numeric_literals[idx]
            if lit.canonical == wanted:
                self._literal_cursor = idx + 1
                return lit.location

        for idx, lit in enumerate(self.numeric_literals):
            if lit.canonical == wanted:
                self._literal_cursor = idx + 1
                return lit.location

        return None


_CACHE: Dict[Tuple[str, float, int], SourceIndex] = {}


def get_source_index(file_path: str) -> SourceIndex:
    """Cached entry point used by rule_engine.py."""
    path = os.path.abspath(file_path)
    try:
        stat = os.stat(path)
        key = (path, stat.st_mtime, stat.st_size)
    except OSError:
        key = (path, 0.0, 0)

    cached = _CACHE.get(key)
    if cached:
        return cached

    index = build_source_index(path)
    _CACHE.clear()
    _CACHE[key] = index
    return index


def build_source_index(file_path: str) -> SourceIndex:
    path = os.path.abspath(file_path)
    try:
        original_text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return SourceIndex(file_path=path)

    stripped_text = strip_comments_preserve_lines(original_text)
    lines = stripped_text.splitlines()

    index = SourceIndex(file_path=path)
    _index_preprocessor(index, path, lines)
    _index_functions(index, path, lines)
    _index_declarations(index, path, lines)
    _index_calls(index, path, lines)
    _index_numeric_literals(index, path, lines)
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


# ============================================================
# Indexers
# ============================================================

def _index_preprocessor(index: SourceIndex, path: str, lines: List[str]) -> None:
    include_re = re.compile(r'^\s*#\s*include\s*([<"])([^>"]+)[>"]')
    define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)(?:\([^)]*\))?\s*(.*)$')

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
                body=macro.group(2).strip(),
            )


def _index_functions(index: SourceIndex, path: str, lines: List[str]) -> None:
    """Index function definitions from original source using bounded logic.

    This intentionally avoids broad regexes such as ``(?:word|space|*)+`` because
    those can catastrophically backtrack on embedded generated declarations.
    """
    control_words = {"if", "for", "while", "switch", "return", "sizeof", "case", "do", "else"}
    signature_parts: List[Tuple[int, str]] = []

    def commit_signature(parts: List[Tuple[int, str]]) -> None:
        if not parts:
            return
        combined = " ".join(txt.strip() for _, txt in parts)
        before_brace = combined.split("{", 1)[0]
        if ";" in before_brace or "(" not in before_brace or ")" not in before_brace:
            return
        # Function name is the identifier immediately before the parameter list.
        m = re.search(r"\b([A-Za-z_]\w*)\s*\([^(){};]*\)\s*$", before_brace.strip())
        if not m:
            return
        name = m.group(1)
        if name in control_words or name in index.functions:
            return
        name_line, name_col = parts[0][0], 1
        for lno, txt in parts:
            pos = txt.find(name)
            if pos >= 0:
                name_line, name_col = lno, pos + 1
                break
        index.functions[name] = FunctionSymbol(
            name=name,
            location=SourceLocation(path, name_line, name_col),
        )

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            signature_parts.clear()
            continue

        # Single-line or closing-line candidate. Do cheap string checks first.
        if "{" in stripped and "(" in stripped and ")" in stripped:
            if signature_parts:
                signature_parts.append((lineno, line))
                commit_signature(signature_parts)
                signature_parts.clear()
            else:
                commit_signature([(lineno, line)])
            continue

        # Bounded multiline signature collection. C signatures are normally short;
        # cap this to avoid accidental accumulation through large initializer blocks.
        if "(" in stripped and not stripped.endswith(";") and not stripped.startswith(tuple(control_words)):
            signature_parts = [(lineno, line)]
            continue

        if signature_parts:
            signature_parts.append((lineno, line))
            combined = " ".join(txt.strip() for _, txt in signature_parts)
            if "{" in combined:
                commit_signature(signature_parts)
                signature_parts.clear()
            elif ";" in combined or len(signature_parts) > 12:
                signature_parts.clear()

    for func in index.functions.values():
        func.end_line = _find_function_end(lines, func.location.line)

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
    control_words = {"if", "for", "while", "switch", "return", "sizeof"}
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
        "int", "float", "double", "bool", "inline",
    }
    control_starts = ("if", "for", "while", "switch", "return", "case", "else", "do", "sizeof")
    type_start_re = re.compile(
        r"^\s*(?:(?:static|const|volatile|extern|register|auto|inline)\s+)*"
        r"(?:(?:struct|union|enum)\s+)?[A-Za-z_]\w*"
    )

    logical_stmt = ""
    stmt_start_line = 1

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            logical_stmt = ""
            continue

        # Prevent function signatures / bare braces from being accumulated into
        # the next declaration. This fixes local static declarations immediately
        # after an opening brace, e.g. `static bool btn_last = false;`.
        if not logical_stmt:
            if stripped in ("{", "}"):
                continue
            if "(" in stripped and ";" not in stripped and "=" not in stripped:
                continue

        if not logical_stmt:
            stmt_start_line = lineno
        logical_stmt += line + "\n"

        # Declaration statement ends at semicolon. This also handles initializer blocks.
        if ";" not in line:
            continue

        statement = logical_stmt.split(";", 1)[0]
        first_line_text = logical_stmt.splitlines()[0] if logical_stmt.splitlines() else ""
        logical_stmt = ""

        stmt_strip = statement.strip()
        if not stmt_strip or stmt_strip.startswith(control_starts):
            continue
        if "(" in _left_of_initializer(statement) and ")" in _left_of_initializer(statement):
            # Function prototype or call-like statement, not variable declaration.
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

            # Locate name in the original statement lines.
            loc_line = stmt_start_line
            loc_col = 1
            for offset, txt in enumerate(statement.splitlines()):
                pos = txt.find(name)
                if pos >= 0:
                    loc_line = stmt_start_line + offset
                    loc_col = pos + 1
                    break

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
