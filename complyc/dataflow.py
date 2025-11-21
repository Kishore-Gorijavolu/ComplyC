# ======================================================================
# dataflow.py – Dataflow Analysis Engine for ComplyC
#
# Provides:
#   - analyze_function_dataflow(func_ast, cfg)
#   - analyze_translation_unit(ast, cfgs)
#
# Returns:
#   For each function:
#       {
#         "uninitialized_uses": [(var, line)],
#         "dead_stores":       [(var, line)],
#         "never_used":        [var],
#         "writes":            { var: [line, ...] },
#       }
# ======================================================================

from __future__ import annotations
from typing import Dict, Set, List, Tuple
from pycparser import c_ast

from .cfg import CFG


# ---------------------------------------------------------
# Dataflow facts
# ---------------------------------------------------------

class DataflowState:
    """
    IN / OUT state at a CFG node:

      initialized : variables definitely initialized on all paths
      used        : variables read at least once along some path
      defined     : variables assigned at least once along some path
    """

    def __init__(self) -> None:
        self.initialized: Set[str] = set()
        self.used: Set[str] = set()
        self.defined: Set[str] = set()

    def copy(self) -> "DataflowState":
        new = DataflowState()
        new.initialized = set(self.initialized)
        new.used = set(self.used)
        new.defined = set(self.defined)
        return new

    def merge(self, other: "DataflowState") -> "DataflowState":
        """
        Forward dataflow merge:

        - initialized : intersection  (definitely initialized)
        - used        : union         (used on any path)
        - defined     : union         (defined on any path)
        """
        merged = DataflowState()
        merged.initialized = self.initialized & other.initialized
        merged.used = self.used | other.used
        merged.defined = self.defined | other.defined
        return merged

    def __repr__(self) -> str:
        return f"(init={self.initialized}, used={self.used}, def={self.defined})"


# ---------------------------------------------------------
# AST visitor to detect variable reads / writes in a node
# ---------------------------------------------------------

class VarUsageExtractor(c_ast.NodeVisitor):
    """
    Extract variable reads and writes from a statement / expression node.
    """

    def __init__(self) -> None:
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()

    def visit_ID(self, node: c_ast.ID):
        # Normal ID occurrence = read
        self.reads.add(node.name)

    def visit_Assignment(self, node: c_ast.Assignment):
        # RHS reads
        self.visit(node.rvalue)

        # LHS write, but don't count it as read again
        if isinstance(node.lvalue, c_ast.ID):
            self.writes.add(node.lvalue.name)
        else:
            # *p = x; → unknown target, ignore for now
            pass

    def visit_Decl(self, node: c_ast.Decl):
        # int x = 5; → write x, plus possible reads in initializer
        if isinstance(node.type, c_ast.TypeDecl) and isinstance(node.type.declname, str):
            name = node.type.declname
            if node.init is not None:
                self.writes.add(name)
        if node.init is not None:
            self.visit(node.init)


# ---------------------------------------------------------
# Function metadata helpers
# ---------------------------------------------------------

def get_function_params(func_ast: c_ast.FuncDef) -> Set[str]:
    """
    Return parameter names. Parameters are considered initialized at entry.
    """
    result: Set[str] = set()
    ftype = func_ast.decl.type
    while hasattr(ftype, "type") and not isinstance(ftype, c_ast.FuncDecl):
        ftype = ftype.type

    if isinstance(ftype, c_ast.FuncDecl) and ftype.args is not None:
        for p in ftype.args.params or []:
            if isinstance(p, c_ast.Decl) and isinstance(p.name, str):
                result.add(p.name)
    return result


def build_function_map(ast: c_ast.FileAST) -> Dict[str, c_ast.FuncDef]:
    """
    Map function name -> FuncDef for all functions in the translation unit.
    """
    funcs: Dict[str, c_ast.FuncDef] = {}
    for ext in ast.ext:
        if isinstance(ext, c_ast.FuncDef):
            funcs[ext.decl.name] = ext
    return funcs


# ---------------------------------------------------------
# Core per-function dataflow
# ---------------------------------------------------------

def analyze_function_dataflow(func_ast: c_ast.FuncDef, cfg: CFG) -> Dict[str, object]:
    """
    Run forward dataflow analysis for a single function.

    Returns:
        {
          "uninitialized_uses": [(var, line)],
          "dead_stores":       [(var, line)],
          "never_used":        [var],
          "writes":            { var: [line, ...] },
        }
    """
    params = get_function_params(func_ast)

    IN: Dict[int, DataflowState] = {n.id: DataflowState() for n in cfg.nodes}
    OUT: Dict[int, DataflowState] = {n.id: DataflowState() for n in cfg.nodes}

    # Seed params as initialized at entry
    if cfg.entry is not None:
        entry_state = IN[cfg.entry.id]
        entry_state.initialized.update(params)
        entry_state.defined.update(params)

    changed = True
    while changed:
        changed = False

        for node in cfg.nodes:
            # IN: merge predecessors (except entry, which keeps its seeded state)
            if node is cfg.entry:
                new_in = IN[node.id].copy()
            elif node.predecessors:
                new_in = IN[node.predecessors[0].id].copy()
                for pred in node.predecessors[1:]:
                    new_in = new_in.merge(IN[pred.id])
            else:
                new_in = DataflowState()

            IN[node.id] = new_in
            out = new_in.copy()

            # Transfer: apply reads/writes for this node
            extractor = VarUsageExtractor()
            if node.ast_node is not None:
                extractor.visit(node.ast_node)

            for r in extractor.reads:
                out.used.add(r)
            for w in extractor.writes:
                out.defined.add(w)
                out.initialized.add(w)

            if (out.initialized != OUT[node.id].initialized or
                out.used != OUT[node.id].used or
                out.defined != OUT[node.id].defined):
                OUT[node.id] = out
                changed = True

    # ----------------- Collect results -----------------

    uninitialized_uses: List[Tuple[str, int]] = []
    dead_stores: List[Tuple[str, int]] = []
    last_write_lines: Dict[str, List[int]] = {}

    for node in cfg.nodes:
        extractor = VarUsageExtractor()
        if node.ast_node is not None:
            extractor.visit(node.ast_node)

        line = getattr(getattr(node.ast_node, "coord", None), "line", None)

        # Uninitialized uses
        for r in extractor.reads:
            if r not in IN[node.id].initialized and r not in params:
                if line is not None:
                    uninitialized_uses.append((r, line))

        # Writes & dead stores
        for w in extractor.writes:
            if line is not None:
                last_write_lines.setdefault(w, []).append(line)
            if w not in OUT[node.id].used and line is not None:
                dead_stores.append((w, line))

    # Vars written but never used anywhere
    never_used: List[str] = []
    for var, _lines in last_write_lines.items():
        used_anywhere = any(var in OUT[n.id].used for n in cfg.nodes)
        if not used_anywhere and var not in params:
            never_used.append(var)

    return {
        "uninitialized_uses": uninitialized_uses,
        "dead_stores": dead_stores,
        "never_used": never_used,
        "writes": last_write_lines,
    }


# ---------------------------------------------------------
# Translation-unit level helper
# ---------------------------------------------------------

def analyze_translation_unit(
    ast: c_ast.FileAST,
    cfgs: Dict[str, CFG],
) -> Dict[str, Dict[str, object]]:
    """
    Run dataflow analysis for every function in the TU.

    Returns:
        { func_name: <result dict from analyze_function_dataflow> }
    """
    func_map = build_function_map(ast)
    results: Dict[str, Dict[str, object]] = {}

    for func_name, cfg in cfgs.items():
        func_ast = func_map.get(func_name)
        if func_ast is None:
            continue
        results[func_name] = analyze_function_dataflow(func_ast, cfg)

    return results
