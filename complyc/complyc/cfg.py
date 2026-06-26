# ======================================================================
# cfg.py – Control Flow Graph (CFG) generator for ComplyC
#
# Integrates with: parser.py (pycparser AST)
# Usage:
#     from complyc.cfg import build_cfg
#     cfgs = build_cfg(ast)
# ======================================================================

from __future__ import annotations
from typing import List, Dict, Optional
from pycparser import c_ast

# -------------------------------------------------------------
# CFG Node
# -------------------------------------------------------------

class CFGNode:
    _id_counter = 1

    def __init__(self, label: str, ast_node=None):
        self.id = CFGNode._id_counter
        CFGNode._id_counter += 1

        self.label = label
        self.ast_node = ast_node
        self.successors: List["CFGNode"] = []
        self.predecessors: List["CFGNode"] = []

    def add_successor(self, node: "CFGNode"):
        if node not in self.successors:
            self.successors.append(node)
        if self not in node.predecessors:
            node.predecessors.append(self)

    def __repr__(self):
        return f"CFGNode({self.id}, label={self.label!r})"


# -------------------------------------------------------------
# CFG object
# -------------------------------------------------------------

class CFG:
    def __init__(self, func_name: str):
        self.func_name = func_name
        self.entry: Optional[CFGNode] = None
        self.exit: Optional[CFGNode] = None
        self.nodes: List[CFGNode] = []

    def add_node(self, node: CFGNode):
        self.nodes.append(node)
        return node

    def compute_cyclomatic_complexity(self) -> int:
        """
        Standard McCabe formula: CC = E - N + 2
        """
        N = len(self.nodes)
        E = sum(len(n.successors) for n in self.nodes)
        return E - N + 2

    def dump(self):
        """Debug dump."""
        print(f"\nCFG for function '{self.func_name}'")
        for n in self.nodes:
            succ_ids = [s.id for s in n.successors]
            print(f"  Node {n.id} ({n.label}) -> {succ_ids}")


# -------------------------------------------------------------
# CFG Builder Visitor
# -------------------------------------------------------------

class CFGBuilder(c_ast.NodeVisitor):
    def __init__(self):
        self.cfgs: Dict[str, CFG] = {}
        self.current_cfg: Optional[CFG] = None

    # --------------- Entry point for function definitions ---------------

    def visit_FuncDef(self, node: c_ast.FuncDef):
        func_name = node.decl.name
        cfg = CFG(func_name)
        self.current_cfg = cfg

        # Create ENTRY and EXIT nodes
        entry = cfg.add_node(CFGNode("ENTRY", ast_node=node))
        exit = cfg.add_node(CFGNode("EXIT", ast_node=node))
        cfg.entry = entry
        cfg.exit = exit

        # Build body CFG
        last = self.build_statement(node.body, entry)

        # Connect last block to exit
        if last is not None:
            last.add_successor(exit)

        self.cfgs[func_name] = cfg
        self.current_cfg = None

    # -------------------------------------------------------------
    # Statement handlers
    # -------------------------------------------------------------

    def build_statement(self, stmt, prev: CFGNode) -> CFGNode:
        """
        Generic handler for any statement node. Returns the last node in chain.
        """
        if stmt is None:
            return prev

        stmt_type = type(stmt).__name__

        # Block (compound) statement
        if isinstance(stmt, c_ast.Compound):
            last = prev
            if stmt.block_items:
                for s in stmt.block_items:
                    last = self.build_statement(s, last)
            return last

        # If statement
        if isinstance(stmt, c_ast.If):
            return self.handle_if(stmt, prev)

        # For loop
        if isinstance(stmt, c_ast.For):
            return self.handle_for(stmt, prev)

        # While loop
        if isinstance(stmt, c_ast.While):
            return self.handle_while(stmt, prev)

        # Return statement (terminate path)
        if isinstance(stmt, c_ast.Return):
            return self.handle_return(stmt, prev)

        # Default: Simple statement node
        label = stmt_type
        node = self.current_cfg.add_node(CFGNode(label, ast_node=stmt))
        prev.add_successor(node)
        return node

    # -------------------------------------------------------------
    # IF / ELSE
    # -------------------------------------------------------------

    def handle_if(self, stmt: c_ast.If, prev: CFGNode) -> CFGNode:
        cond = self.current_cfg.add_node(CFGNode("IF_COND", ast_node=stmt.cond))
        prev.add_successor(cond)

        # True branch
        true_end = self.build_statement(stmt.iftrue, cond)

        # False branch
        if stmt.iffalse:
            false_end = self.build_statement(stmt.iffalse, cond)
        else:
            false_end = cond  # empty else

        # Merge point
        merge = self.current_cfg.add_node(CFGNode("IF_MERGE"))
        true_end.add_successor(merge)
        if false_end is not cond:
            false_end.add_successor(merge)
        else:
            cond.add_successor(merge)

        return merge

    # -------------------------------------------------------------
    # WHILE loop
    # -------------------------------------------------------------

    def handle_while(self, stmt: c_ast.While, prev: CFGNode) -> CFGNode:
        cond = self.current_cfg.add_node(CFGNode("WHILE_COND", ast_node=stmt.cond))
        prev.add_successor(cond)

        # Body
        body_end = self.build_statement(stmt.stmt, cond)
        body_end.add_successor(cond)

        # After-loop
        after = self.current_cfg.add_node(CFGNode("WHILE_AFTER"))
        cond.add_successor(after)

        return after

    # -------------------------------------------------------------
    # FOR loop
    # -------------------------------------------------------------

    def handle_for(self, stmt: c_ast.For, prev: CFGNode) -> CFGNode:
        init = self.current_cfg.add_node(CFGNode("FOR_INIT", ast_node=stmt.init))
        prev.add_successor(init)

        cond = self.current_cfg.add_node(CFGNode("FOR_COND", ast_node=stmt.cond))
        init.add_successor(cond)

        body_end = self.build_statement(stmt.stmt, cond)

        nextop = self.current_cfg.add_node(CFGNode("FOR_NEXT", ast_node=stmt.next))
        body_end.add_successor(nextop)
        nextop.add_successor(cond)

        after = self.current_cfg.add_node(CFGNode("FOR_AFTER"))
        cond.add_successor(after)

        return after

    # -------------------------------------------------------------
    # Return
    # -------------------------------------------------------------

    def handle_return(self, stmt: c_ast.Return, prev: CFGNode) -> CFGNode:
        node = self.current_cfg.add_node(CFGNode("RETURN", ast_node=stmt))
        prev.add_successor(node)

        # Return goes directly to EXIT
        node.add_successor(self.current_cfg.exit)
        return node


# -------------------------------------------------------------
# Public API
# -------------------------------------------------------------

def build_cfg(ast: c_ast.FileAST) -> Dict[str, CFG]:
    """
    Build CFGs for all functions in the translation unit.
    Returns { func_name: CFG }
    """
    builder = CFGBuilder()
    builder.visit(ast)
    return builder.cfgs
