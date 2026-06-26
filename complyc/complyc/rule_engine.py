"""
rule_engine.py – Core engine for ComplyC
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from pycparser import c_ast


@dataclass
class Violation:
    rule_id: str
    message: str
    file: str
    line: Optional[int] = None
    severity: Optional[str] = None
    reference: Optional[str] = None


# ---------- parent map helper ----------

def build_parent_map(ast: c_ast.FileAST) -> Dict[c_ast.Node, c_ast.Node]:
    parent: Dict[c_ast.Node, c_ast.Node] = {}

    class P(c_ast.NodeVisitor):
        def generic_visit(self, node):
            for _, child in node.children():
                parent[child] = node
                self.visit(child)

    P().visit(ast)
    return parent


# ---------- scope iterator ----------

def iter_nodes_by_scope(ast: c_ast.FileAST, scope: str):
    if scope == "file":
        yield ast, {}
        return

    class Visitor(c_ast.NodeVisitor):
        def __init__(self):
            self.results: List[tuple] = []

        def visit_FuncDef(self, node: c_ast.FuncDef):
            if scope == "function":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Decl(self, node: c_ast.Decl):
            storage = node.storage or []
            is_static = "static" in storage

            if scope == "variable":
                self.results.append((node, {"is_static": is_static}))
            elif scope == "static_variable" and is_static:
                self.results.append((node, {"is_static": True}))
            elif scope == "global_variable" and not is_static:
                self.results.append((node, {"is_static": False}))

            if scope == "typedef" and "typedef" in storage:
                self.results.append((node, {}))

            self.generic_visit(node)

        def visit_FuncCall(self, node: c_ast.FuncCall):
            if scope == "call_expression":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_If(self, node: c_ast.If):
            if scope in ("if_statement", "condition"):
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_For(self, node: c_ast.For):
            if scope in ("loop_statement", "for_statement"):
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_While(self, node: c_ast.While):
            if scope in ("loop_statement", "while_statement"):
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Switch(self, node: c_ast.Switch):
            if scope == "switch_statement":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Struct(self, node: c_ast.Struct):
            if scope == "struct_definition":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Enum(self, node: c_ast.Enum):
            if scope == "enum_definition":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Enumerator(self, node: c_ast.Enumerator):
            if scope == "enum_constant":
                self.results.append((node, {}))
            self.generic_visit(node)

        def visit_Constant(self, node: c_ast.Constant):
            if scope == "literal":
                self.results.append((node, {}))
            self.generic_visit(node)

    v = Visitor()
    v.visit(ast)
    for n, extra in v.results:
        yield n, extra


# ---------- helpers ----------

def get_node_name(node: Any) -> Optional[str]:
    if hasattr(node, "name") and isinstance(node.name, str):
        return node.name
    if hasattr(node, "decl") and hasattr(node.decl, "name"):
        return node.decl.name
    return None


# ---------- core checks ----------

def check_regex(node, rule, ctx) -> List[Violation]:
    name = get_node_name(node)
    if not name:
        return []
    pattern = rule.get("pattern")
    if not pattern:
        return []
    if not re.match(pattern, name):
        return [Violation(
            rule_id=rule["id"],
            message=f"Name '{name}' does not match pattern '{pattern}'. {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=getattr(node.coord, "line", None),
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []

def check_global_naming(node, rule, ctx) -> List[Violation]:
    """
    Enforce naming rule for *global variables only*:
    - A global variable is a Decl whose parent is the FileAST
      and whose type is NOT a function (i.e., not a FuncDecl).
    - Functions, parameters, and local variables are ignored.
    """
    from pycparser import c_ast  # local import just to be explicit

    # We only expect this to be called with the FileAST because scope: file
    if not isinstance(node, c_ast.FileAST):
        return []

    parent_map = ctx.get("parent_map", {})
    pattern = rule.get("pattern")
    if not pattern:
        return []

    regex = re.compile(pattern)
    violations: List[Violation] = []

    class GlobalVarVisitor(c_ast.NodeVisitor):
        def visit_Decl(self, decl: c_ast.Decl):
            # Determine if this Decl is at top level (child of FileAST)
            parent = parent_map.get(decl)

            if isinstance(parent, c_ast.FileAST):
                # Now distinguish between:
                # - function declarations/prototypes (FuncDecl)
                # - true variables (anything else)
                decl_type = decl.type
                # Unwrap nested types until we reach the base
                while hasattr(decl_type, "type") and not isinstance(decl_type, c_ast.FuncDecl):
                    decl_type = decl_type.type

                # If base is FuncDecl -> it's a function, not a variable
                if isinstance(decl_type, c_ast.FuncDecl):
                    return  # skip functions

                # This is a real global variable
                name = decl.name
                if name is None:
                    return

                if not regex.match(name):
                    violations.append(Violation(
                        rule_id=rule["id"],
                        message=f"Global variable '{name}' does not match pattern '{pattern}'. {rule.get('guidance','')}",
                        file=ctx["file_path"],
                        line=getattr(decl.coord, "line", None),
                        severity=rule.get("severity"),
                        reference=rule.get("reference"),
                    ))

            # Continue walking (there might be more Decls)
            self.generic_visit(decl)

    GlobalVarVisitor().visit(node)
    return violations

def check_max_function_length(node: c_ast.FuncDef, rule, ctx) -> List[Violation]:
    if not node.coord:
        return []
    start = node.coord.line
    end = start
    if node.body and getattr(node.body, "block_items", None):
        last = node.body.block_items[-1]
        if last and last.coord:
            end = last.coord.line
    length = end - start + 1
    max_lines = rule.get("max_lines", 40)
    if length > max_lines:
        return [Violation(
            rule_id=rule["id"],
            message=f"Function '{node.decl.name}' has {length} lines (max {max_lines}). {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=start,
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []


def check_max_parameter_count(node: c_ast.FuncDef, rule, ctx) -> List[Violation]:
    func_type = node.decl.type
    while hasattr(func_type, "type") and not isinstance(func_type, c_ast.FuncDecl):
        func_type = func_type.type

    if isinstance(func_type, c_ast.FuncDecl):
        params = getattr(func_type.args, "params", []) or []
        count = len(params)
        max_params = rule.get("max_parameters", 6)
        if count > max_params:
            return [Violation(
                rule_id=rule["id"],
                message=f"Function '{node.decl.name}' has {count} parameters (max {max_params}). {rule.get('guidance', '')}",
                file=ctx["file_path"],
                line=node.coord.line if node.coord else None,
                severity=rule.get("severity"),
                reference=rule.get("reference"),
            )]
    return []


def check_forbidden_functions(node: c_ast.FuncCall, rule, ctx) -> List[Violation]:
    if not isinstance(node.name, c_ast.ID):
        return []
    func_name = node.name.name
    forbidden = set(rule.get("functions", []))
    if func_name in forbidden:
        return [Violation(
            rule_id=rule["id"],
            message=f"Call to forbidden function '{func_name}'. {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=node.coord.line if node.coord else None,
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []


def check_file_header_contains(node, rule, ctx) -> List[Violation]:
    # node is the FileAST
    file_lines = ctx["file_lines"]
    required = rule.get("required_lines", [])
    missing = [s for s in required if not any(s in line for line in file_lines[:20])]
    if missing:
        return [Violation(
            rule_id=rule["id"],
            message=f"File is missing header entries: {', '.join(missing)}. {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=1,
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []


def check_max_cyclomatic_complexity(node: c_ast.FuncDef, rule, ctx) -> List[Violation]:
    class CCVisitor(c_ast.NodeVisitor):
        def __init__(self):
            self.cc = 1

        def visit_If(self, n):
            self.cc += 1
            self.generic_visit(n)

        def visit_For(self, n):
            self.cc += 1
            self.generic_visit(n)

        def visit_While(self, n):
            self.cc += 1
            self.generic_visit(n)

        def visit_Case(self, n):
            self.cc += 1
            self.generic_visit(n)

        def visit_Default(self, n):
            self.cc += 1
            self.generic_visit(n)

    v = CCVisitor()
    v.visit(node)
    max_cc = rule.get("max_cc", 10)
    if v.cc > max_cc:
        return [Violation(
            rule_id=rule["id"],
            message=f"Function '{node.decl.name}' has CC={v.cc} (max {max_cc}). {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=node.coord.line if node.coord else None,
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []


def check_max_nesting_depth(node: c_ast.FuncDef, rule, ctx) -> List[Violation]:
    class NestVisitor(c_ast.NodeVisitor):
        def __init__(self):
            self.max_depth = 0
            self.current = 0

        def _enter(self):
            self.current += 1
            self.max_depth = max(self.max_depth, self.current)

        def _exit(self):
            self.current -= 1

        def visit_If(self, n):
            self._enter()
            self.generic_visit(n)
            self._exit()

        def visit_For(self, n):
            self._enter()
            self.generic_visit(n)
            self._exit()

        def visit_While(self, n):
            self._enter()
            self.generic_visit(n)
            self._exit()

        def visit_Switch(self, n):
            self._enter()
            self.generic_visit(n)
            self._exit()

    v = NestVisitor()
    v.visit(node)
    max_depth = rule.get("max_depth", 4)
    if v.max_depth > max_depth:
        return [Violation(
            rule_id=rule["id"],
            message=f"Function '{node.decl.name}' nesting depth={v.max_depth} (max {max_depth}). {rule.get('guidance', '')}",
            file=ctx["file_path"],
            line=node.coord.line if node.coord else None,
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        )]
    return []


# ---- magic number helper & check ----

def _strip_int_suffixes(tok: str) -> str:
    return re.sub(r'[uUlL]+$', '', tok)

def _parse_int_literal(tok: str) -> Optional[int]:
    s = _strip_int_suffixes(tok)
    try:
        if s.lower().startswith("0x"):
            return int(s, 16)
        if len(s) > 1 and s.startswith("0") and s.isdigit():
            try:
                return int(s, 8)
            except ValueError:
                return int(s, 10)
        return int(s, 10)
    except ValueError:
        return None

def _strip_float_suffixes(tok: str) -> str:
    return re.sub(r'[fFlL]$', '', tok)

def _parse_float_literal(tok: str) -> Optional[float]:
    s = _strip_float_suffixes(tok)
    try:
        return float(s)
    except ValueError:
        return None

def _is_under_enum(node, parent_map) -> bool:
    cur = node
    while cur in parent_map:
        cur = parent_map[cur]
        if isinstance(cur, (c_ast.Enum, c_ast.Enumerator)):
            return True
    return False

def _effective_numeric_value(node, parent_map) -> Tuple[Optional[float], str]:
    if not isinstance(node, c_ast.Constant):
        return (None, "")
    if node.type == "char":
        return (None, "")
    raw = node.value
    sign = 1
    parent = parent_map.get(node)
    if isinstance(parent, c_ast.UnaryOp) and parent.op == "-":
        sign = -1
    if node.type == "int":
        ival = _parse_int_literal(raw)
        return ((sign * ival) if ival is not None else None, "int")
    elif node.type == "float":
        fval = _parse_float_literal(raw)
        return ((sign * fval) if fval is not None else None, "float")
    return (None, "")

def check_magic_number(node, rule, ctx) -> List[Violation]:
    parent_map = ctx.get("parent_map", {})
    allow_in_enum = rule.get("allow_in_enum", True)

    if not isinstance(node, (c_ast.Constant, c_ast.FileAST)):
        return []

    violations: List[Violation] = []

    def maybe_flag(cn: c_ast.Constant):
        val, kind = _effective_numeric_value(cn, parent_map)
        if val is None:
            return
        ignore_vals = set()
        for v in rule.get("ignore_values", []):
            try:
                ignore_vals.add(int(v))
            except Exception:
                try:
                    ignore_vals.add(float(v))
                except Exception:
                    pass
        if val in ignore_vals:
            return
        if allow_in_enum and _is_under_enum(cn, parent_map):
            return
        violations.append(Violation(
            rule_id=rule["id"],
            message=f"Magic number {cn.value!r} detected. {rule.get('guidance','Define a named constant.')}",
            file=ctx["file_path"],
            line=getattr(cn.coord, "line", None),
            severity=rule.get("severity"),
            reference=rule.get("reference"),
        ))

    if isinstance(node, c_ast.FileAST):
        class LitVisitor(c_ast.NodeVisitor):
            def visit_Constant(self, cn):
                maybe_flag(cn)
        LitVisitor().visit(node)
        return violations

    maybe_flag(node)
    return violations


# ---------- dispatcher ----------

CHECK_HANDLERS: Dict[str, Callable[[Any, Dict[str, Any], Dict[str, Any]], List[Violation]]] = {
    "regex": check_regex,
    "max_function_length": check_max_function_length,
    "max_parameter_count": check_max_parameter_count,
    "forbidden_functions": check_forbidden_functions,
    "file_header_contains": check_file_header_contains,
    "max_cyclomatic_complexity": check_max_cyclomatic_complexity,
    "max_nesting_depth": check_max_nesting_depth,
    "magic_number": check_magic_number,
    "global_naming": check_global_naming,
}


# ---------- main entry ----------

def run_rules(ast: c_ast.FileAST, rules: List[Dict[str, Any]], file_path: str) -> List[Violation]:
    with open(file_path, "r", encoding="utf-8") as f:
        file_lines = f.readlines()

    parent_map = build_parent_map(ast)

    ctx_base = {
        "file_path": file_path,
        "file_lines": file_lines,
        "parent_map": parent_map,
    }

    all_violations: List[Violation] = []

    for rule in rules:
        scope = rule.get("scope", "file")
        check_name = rule.get("check")
        if not check_name:
            continue
        handler = CHECK_HANDLERS.get(check_name)
        if handler is None:
            continue

        for node, extra in iter_nodes_by_scope(ast, scope):
            ctx = {**ctx_base, **extra}
            try:
                vio = handler(node, rule, ctx)
            except Exception as e:
                print(f"[ComplyC] Error in rule {rule.get('id')}: {e}")
                vio = []
            all_violations.extend(vio)

    return all_violations
