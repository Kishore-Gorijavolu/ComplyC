"""
source_callgraph.py - Original-source index and call-graph support for ComplyC.

Purpose:
    pycparser coordinates can drift when GCC preprocessing injects included headers,
    fake typedefs, or macro-expanded code. This module builds a lightweight index
    from the ORIGINAL .c/.h source text and is used as the final authority for
    user-facing report locations.

It is intentionally conservative:
    - Function definitions are indexed by name.
    - Declarations are indexed by identifier name.
    - Numeric literals are indexed from original source text only.
      Therefore macro-expanded constants are naturally suppressed from magic-number
      reports because the expanded value does not exist as a raw literal on the
      original usage line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: int = 1


@dataclass
class FunctionRecord:
    name: str
    location: SourceLocation
    end_line: Optional[int] = None
    calls: List[Tuple[str, SourceLocation]] = field(default_factory=list)


@dataclass
class SourceCallGraph:
    file_path: str
    functions: Dict[str, FunctionRecord] = field(default_factory=dict)
    declarations: Dict[str, List[SourceLocation]] = field(default_factory=dict)
    numeric_literals: List[Tuple[str, SourceLocation]] = field(default_factory=list)

    _literal_cursor: int = 0

    def find_function(self, name: Optional[str]) -> Optional[SourceLocation]:
        if not name:
            return None
        rec = self.functions.get(name)
        return rec.location if rec else None

    def find_declaration(self, name: Optional[str], preferred_line: Optional[int] = None) -> Optional[SourceLocation]:
        if not name:
            return None
        locs = self.declarations.get(name) or []
        if not locs:
            return None
        if preferred_line is None:
            return locs[0]
        return min(locs, key=lambda loc: abs(loc.line - int(preferred_line)))

    def has_declaration(self, name: Optional[str]) -> bool:
        return bool(name and self.declarations.get(name))

    def next_numeric_literal(self, token: str) -> Optional[SourceLocation]:
        """
        Return the next matching numeric literal location from original source.
        AST traversal is normally source ordered, so this gives stable locations
        without trusting preprocessed line numbers.
        """
        wanted = _canonical_numeric_token(token)
        if wanted is None:
            return None

        for idx in range(self._literal_cursor, len(self.numeric_literals)):
            raw, loc = self.numeric_literals[idx]
            if _canonical_numeric_token(raw) == wanted:
                self._literal_cursor = idx + 1
                return loc

        # Fallback: search from beginning for repeated rule invocations.
        for idx, (raw, loc) in enumerate(self.numeric_literals):
            if _canonical_numeric_token(raw) == wanted:
                self._literal_cursor = idx + 1
                return loc

        return None


_CACHE: Dict[Tuple[str, float], SourceCallGraph] = {}


def get_source_callgraph(file_path: str) -> SourceCallGraph:
    path = os.path.abspath(file_path)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0

    key = (path, mtime)
    cached = _CACHE.get(key)
    if cached:
        return cached

    graph = build_source_callgraph(path)
    _CACHE.clear()  # avoid stale source maps when files are edited repeatedly
    _CACHE[key] = graph
    return graph


def build_source_callgraph(file_path: str) -> SourceCallGraph:
    path = os.path.abspath(file_path)
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return SourceCallGraph(file_path=path)

    lines = text.splitlines()
    stripped_lines = _strip_comments_preserve_lines(text).splitlines()
    graph = SourceCallGraph(file_path=path)

    _index_functions_and_calls(graph, path, stripped_lines)
    _index_declarations(graph, path, stripped_lines)
    _index_numeric_literals(graph, path, stripped_lines)

    return graph


def _strip_comments_preserve_lines(text: str) -> str:
    """Remove C comments while preserving newlines and rough columns."""
    result = []
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


def _index_functions_and_calls(graph: SourceCallGraph, path: str, lines: List[str]) -> None:
    # Matches normal C function definitions, including return type on prior text,
    # but excludes if/for/while/switch and prototypes ending in ';'.
    func_re = re.compile(
        r"^\s*(?:[A-Za-z_][\w\s\*]*\s+)+(?P<name>[A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:\{|$)"
    )
    control_words = {"if", "for", "while", "switch", "return", "sizeof"}

    function_stack: List[Tuple[str, int, int]] = []  # name, brace_depth_at_start, start_line
    brace_depth = 0

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            brace_depth += line.count("{") - line.count("}")
            continue

        match = func_re.match(line)
        if match and ";" not in line[: line.find("{") if "{" in line else len(line)]:
            name = match.group("name")
            if name not in control_words and name not in graph.functions:
                col = line.find(name) + 1
                graph.functions[name] = FunctionRecord(
                    name=name,
                    location=SourceLocation(path, lineno, max(col, 1)),
                )

        # Record simple function calls inside current function body.
        current_func = _active_function(graph, lineno)
        if current_func:
            for call in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", line):
                call_name = call.group(1)
                if call_name not in control_words and call_name != current_func.name:
                    current_func.calls.append((call_name, SourceLocation(path, lineno, call.start(1) + 1)))

        brace_depth += line.count("{") - line.count("}")

    # Fill end lines using brace matching after functions are discovered.
    for func in graph.functions.values():
        func.end_line = _find_function_end(lines, func.location.line)


def _active_function(graph: SourceCallGraph, lineno: int) -> Optional[FunctionRecord]:
    for func in graph.functions.values():
        if func.location.line < lineno and (func.end_line is None or lineno <= func.end_line):
            return func
    return None


def _find_function_end(lines: List[str], start_line: int) -> Optional[int]:
    depth = 0
    seen_open = False
    for idx in range(start_line - 1, len(lines)):
        line = lines[idx]
        for ch in line:
            if ch == "{":
                depth += 1
                seen_open = True
            elif ch == "}":
                depth -= 1
                if seen_open and depth <= 0:
                    return idx + 1
    return None


def _index_declarations(graph: SourceCallGraph, path: str, lines: List[str]) -> None:
    """
    Index variable declarations from ORIGINAL source only.

    This index is used to keep user-facing reports anchored to the scanned
    source file and to suppress AST declarations that came only from included
    headers/preprocessed output.
    """
    keywords = {
        "if", "for", "while", "switch", "return", "sizeof", "case", "else", "do",
        "typedef", "struct", "union", "enum", "const", "volatile", "static", "extern",
        "register", "auto", "signed", "unsigned", "short", "long", "void", "char",
        "int", "float", "double", "bool",
    }

    type_start_re = re.compile(
        r"^\s*(?:(?:static|const|volatile|extern|register)\s+)*"
        r"(?:(?:struct|union|enum)\s+)?[A-Za-z_]\w*"
    )

    def split_top_level_commas(text: str) -> List[str]:
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

    def left_of_initializer(text: str) -> str:
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

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ";" not in stripped:
            continue

        before_semicolon = line.split(";", 1)[0]
        lhs = left_of_initializer(before_semicolon)

        # Skip function prototypes/calls and control statements.
        if "(" in lhs and ")" in lhs:
            continue
        first_id_match = re.search(r"\b[A-Za-z_]\w*\b", lhs)
        if first_id_match and first_id_match.group(0) in {"if", "for", "while", "switch", "return", "case", "else", "do", "sizeof"}:
            continue
        if not type_start_re.match(lhs):
            continue

        declarator_parts = split_top_level_commas(before_semicolon)
        for index, part in enumerate(declarator_parts):
            candidate = left_of_initializer(part)
            candidate = re.sub(r"\[[^\]]*\]", "", candidate)
            candidate = candidate.replace("*", " ").strip()
            ids = re.findall(r"\b[A-Za-z_]\w*\b", candidate)
            if not ids:
                continue
            name = ids[-1]
            if name in keywords:
                continue

            # On the first declarator, require at least one type/storage token
            # before the variable name. This avoids treating plain expressions
            # as declarations.
            if index == 0 and len(ids) < 2:
                continue

            col = line.find(name) + 1
            if col <= 0:
                col = 1
            graph.declarations.setdefault(name, []).append(SourceLocation(path, lineno, col))

def _index_numeric_literals(graph: SourceCallGraph, path: str, lines: List[str]) -> None:
    number_re = re.compile(
        r"(?<![A-Za-z0-9_])"
        r"(?:0[xX][0-9A-Fa-f]+[uUlL]*|\d+\.\d*(?:[eE][+-]?\d+)?[fFlL]?|\d+(?:[eE][+-]?\d+)[fFlL]?|\d+[uUlL]*)"
        r"(?![A-Za-z0-9_])"
    )

    for lineno, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # Do not report numbers from #define/#if/#include as magic numbers.
            continue
        for match in number_re.finditer(line):
            graph.numeric_literals.append((match.group(0), SourceLocation(path, lineno, match.start() + 1)))


def _canonical_numeric_token(token: str) -> Optional[str]:
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
