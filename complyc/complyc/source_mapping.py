"""
source_mapping.py – Source location mapping for ComplyC.

This module translates analyzer coordinates back to the user's original source
files. The first supported producer is GCC/CPP line markers emitted during
preprocessing. The API is intentionally small so later engines can add Clang
compile-command mappings, macro-expansion ranges, and include-file ownership
without changing rule checks.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class SourceLocation:
    """Original source location corresponding to an analyzed coordinate."""

    file: str
    line: int
    column: Optional[int] = None
    mapped: bool = True

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class SourceMap:
    """
    One translation-unit source map.

    The key is the physical line number seen by pycparser after preprocessing.
    The value is the original file and line reported by the preprocessor.
    """

    def __init__(self, translation_unit: str):
        self.translation_unit = normalize_path(translation_unit)
        self._line_map: Dict[int, SourceLocation] = {}

    def add(self, analyzed_line: int, source_file: str, source_line: int) -> None:
        self._line_map[int(analyzed_line)] = SourceLocation(
            file=normalize_path(source_file) if not source_file.startswith("<") else source_file,
            line=int(source_line),
            mapped=True,
        )

    def resolve(self, analyzed_line: Optional[int], column: Optional[int] = None) -> Optional[SourceLocation]:
        if analyzed_line is None:
            return None
        loc = self._line_map.get(int(analyzed_line))
        if loc is None:
            return None
        if column is None:
            return loc
        return SourceLocation(file=loc.file, line=loc.line, column=column, mapped=loc.mapped)

    def to_dict(self) -> Dict[str, object]:
        return {
            "translation_unit": self.translation_unit,
            "entries": {
                str(k): v.to_dict() for k, v in sorted(self._line_map.items())
            },
        }


class SourceMappingEngine:
    """Registry and resolver for all translation-unit source maps."""

    def __init__(self):
        self._maps: Dict[str, SourceMap] = {}

    def register(self, translation_unit: str, source_map: SourceMap) -> None:
        self._maps[normalize_path(translation_unit)] = source_map

    def get(self, translation_unit: str) -> Optional[SourceMap]:
        return self._maps.get(normalize_path(translation_unit))

    def resolve(
        self,
        translation_unit: str,
        analyzed_line: Optional[int],
        column: Optional[int] = None,
    ) -> Optional[SourceLocation]:
        source_map = self.get(translation_unit)
        if source_map is None:
            return None
        return source_map.resolve(analyzed_line, column)

    def clear(self) -> None:
        self._maps.clear()


SOURCE_MAPPING_ENGINE = SourceMappingEngine()


def normalize_path(path: str) -> str:
    """Return a stable absolute path key for cross-platform map lookup."""
    return os.path.normcase(os.path.abspath(path))


def build_gcc_source_map(preprocessed_code: str, fallback_file: str) -> SourceMap:
    """
    Build a SourceMap from GCC/CPP line markers.

    GCC emits markers such as:
        # 1 "C:/project/src/button.c"
        # 25 "C:/project/inc/button.h" 1

    The marker applies to the next emitted physical line. ComplyC keeps the
    marker line itself in the physical line count as a blank line before parsing,
    so this map also assigns that physical line for stable coordinates.
    """
    source_map = SourceMap(fallback_file)
    current_file = normalize_path(fallback_file)
    current_line = 1
    line_directive_re = re.compile(r'^\s*#\s+(\d+)\s+"([^"]+)"')

    for analyzed_line, text in enumerate(preprocessed_code.splitlines(), start=1):
        match = line_directive_re.match(text)
        if match:
            marker_line = max(1, int(match.group(1)))
            marker_file = match.group(2)

            # GCC emits pseudo files such as <built-in> and <command-line>.
            # They are not useful for user-facing diagnostics, so keep the
            # previous real file context and map the marker line there.
            if marker_file.startswith("<"):
                source_map.add(analyzed_line, current_file, max(1, current_line))
                continue

            current_line = marker_line
            current_file = marker_file
            if not os.path.isabs(current_file):
                current_file = normalize_path(current_file)
            source_map.add(analyzed_line, current_file, current_line)
            continue

        source_map.add(analyzed_line, current_file, current_line)
        current_line += 1

    return source_map


def register_identity_source_map(path: str, text: str, analyzed_line_offset: int = 0) -> SourceMap:
    """Register a near 1:1 map for builtin preprocessing mode.

    analyzed_line_offset is used when synthetic typedefs are prepended before
    parsing. Lines inside the synthetic region map to source line 1; remaining
    analyzed lines are shifted back to original-file lines.
    """
    source_map = SourceMap(path)
    normalized = normalize_path(path)
    original_line_count = max(1, len(text.splitlines()))

    for analyzed_line in range(1, analyzed_line_offset + original_line_count + 1):
        if analyzed_line <= analyzed_line_offset:
            source_line = 1
        else:
            source_line = analyzed_line - analyzed_line_offset
        source_map.add(analyzed_line, normalized, source_line)

    SOURCE_MAPPING_ENGINE.register(path, source_map)
    return source_map


def register_gcc_source_map(path: str, preprocessed_code: str) -> SourceMap:
    """Build and register a GCC line-marker source map."""
    source_map = build_gcc_source_map(preprocessed_code, path)
    SOURCE_MAPPING_ENGINE.register(path, source_map)
    return source_map
