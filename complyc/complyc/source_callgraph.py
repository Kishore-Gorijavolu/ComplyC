"""
Backward-compatible wrapper for the Source Index Engine.

Older ComplyC code imported source_callgraph.py. The implementation has moved
to source_index_engine.py. Keep this wrapper so existing imports continue to
work without maintaining two independent indexing engines.
"""

from .source_index_engine import (  # noqa: F401
    SIE_VERSION,
    SourceLocation,
    FunctionSymbol,
    DeclarationSymbol,
    MacroSymbol,
    IncludeSymbol,
    NumericLiteral,
    SourceIndex,
    SourceCallGraph,
    FunctionRecord,
    get_source_index,
    build_source_index,
    get_source_callgraph,
    build_source_callgraph,
    clear_source_index_cache,
    canonical_numeric_token,
)
