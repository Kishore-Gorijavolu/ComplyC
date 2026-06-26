"""
project_discovery.py – Project-aware discovery for ComplyC.

Purpose:
    Detect embedded project layout, collect C source files, collect folders
    containing header files, and collect compiler defines where possible.

Supported now:
    - Generic recursive projects
    - TI CCS marker detection
    - VS Code c_cpp_properties.json includePath/defines
    - CMake / Make marker detection
    - MPLAB X marker detection

This file intentionally keeps discovery simple and safe. It does not execute
build scripts or IDE tooling.
"""
from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Set


EXCLUDED_DIR_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "build",
    "debug",
    "release",
    "out",
    "dist",
    "reports",
    "__pycache__",
    ".settings",
    ".launches",
    "node_modules",
    "cmake-build-debug",
    "cmake-build-release",
}

SOURCE_EXTENSIONS = {".c"}
HEADER_EXTENSIONS = {".h", ".hpp", ".hh"}


@dataclass
class ProjectInfo:
    project_root: str
    project_type: str = "Generic"
    source_files: List[str] = field(default_factory=list)
    header_dirs: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _norm(path: Path | str) -> str:
    return str(Path(path).resolve())


def _should_skip_dir(dirname: str) -> bool:
    return dirname.lower() in EXCLUDED_DIR_NAMES


def detect_project_type(project_root: str) -> str:
    root = Path(project_root)

    if (root / ".ccsproject").exists() or (root / ".cproject").exists():
        return "TI CCS"
    if (root / "nbproject").is_dir():
        return "MPLAB X"
    if (root / ".vscode" / "c_cpp_properties.json").exists():
        return "VS Code"
    if (root / "CMakeLists.txt").exists():
        return "CMake"
    if (root / "Makefile").exists() or (root / "makefile").exists():
        return "Makefile"
    return "Generic"


def discover_files_and_header_dirs(project_root: str) -> tuple[List[str], List[str]]:
    source_files: list[str] = []
    header_dirs: set[str] = set()

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]

        current = Path(root)
        for name in files:
            suffix = Path(name).suffix.lower()
            full_path = current / name

            if suffix in SOURCE_EXTENSIONS:
                source_files.append(_norm(full_path))
            elif suffix in HEADER_EXTENSIONS:
                header_dirs.add(_norm(current))

    return sorted(source_files), sorted(header_dirs)


def _expand_vscode_path(raw: str, project_root: str) -> str | None:
    if not raw:
        return None
    value = raw.replace("${workspaceFolder}", project_root)
    value = value.replace("${workspaceRoot}", project_root)
    value = value.replace("${workspaceFolderBasename}", Path(project_root).name)

    # c_cpp_properties may contain /** recursive wildcard. GCC needs real -I dirs.
    value = value.replace("/**", "")
    path = Path(value)
    if not path.is_absolute():
        path = Path(project_root) / path
    return _norm(path)


def discover_vscode(project_root: str) -> tuple[Set[str], Set[str], List[str]]:
    include_dirs: set[str] = set()
    defines: set[str] = set()
    notes: list[str] = []

    cfg = Path(project_root) / ".vscode" / "c_cpp_properties.json"
    if not cfg.exists():
        return include_dirs, defines, notes

    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        configs = data.get("configurations", [])
        for config in configs:
            for inc in config.get("includePath", []) or []:
                expanded = _expand_vscode_path(str(inc), project_root)
                if expanded and Path(expanded).exists():
                    include_dirs.add(expanded)
            for define in config.get("defines", []) or []:
                defines.add(str(define))
        notes.append("Read .vscode/c_cpp_properties.json")
    except Exception as exc:
        notes.append(f"Could not read VS Code configuration: {exc}")

    return include_dirs, defines, notes


def discover_ti_ccs(project_root: str) -> tuple[Set[str], Set[str], List[str]]:
    """
    Best-effort extraction from TI/Eclipse .cproject.
    CCS files vary by version; this intentionally searches attributes/text for
    include-path and define-style values instead of depending on one schema.
    """
    include_dirs: set[str] = set()
    defines: set[str] = set()
    notes: list[str] = []

    cproject = Path(project_root) / ".cproject"
    if not cproject.exists():
        return include_dirs, defines, notes

    try:
        text = cproject.read_text(encoding="utf-8", errors="ignore")

        # Common Eclipse/CDT forms: valueType="includePath" value="..."
        for match in re.finditer(r'valueType="includePath"[^>]*value="([^"]+)"', text):
            raw = match.group(1).replace("&quot;", "").replace("${ProjDirPath}", project_root)
            path = Path(raw)
            if not path.is_absolute():
                path = Path(project_root) / raw
            if path.exists():
                include_dirs.add(_norm(path))

        # Generic include path options often contain -I or --include_path.
        for match in re.finditer(r'(?:-I|--include_path=|--include_path\s+)([^\s;&quot;<>]+)', text):
            raw = match.group(1).replace("${ProjDirPath}", project_root)
            path = Path(raw)
            if not path.is_absolute():
                path = Path(project_root) / raw
            if path.exists():
                include_dirs.add(_norm(path))

        # Defines: -DNAME or NAME=VALUE in define option nodes.
        for match in re.finditer(r'(?:-D)([A-Za-z_][A-Za-z0-9_]*(?:=[^\s;&quot;<>]+)?)', text):
            defines.add(match.group(1))

        notes.append("Read TI CCS .cproject best-effort")
    except Exception as exc:
        notes.append(f"Could not read TI CCS .cproject: {exc}")

    return include_dirs, defines, notes


def discover_mplabx(project_root: str) -> tuple[Set[str], Set[str], List[str]]:
    include_dirs: set[str] = set()
    defines: set[str] = set()
    notes: list[str] = []

    nb = Path(project_root) / "nbproject"
    if not nb.is_dir():
        return include_dirs, defines, notes

    for file_name in ("configurations.xml", "Makefile-impl.mk"):
        path = nb / file_name
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'(?:-I)([^\s;&quot;<>]+)', text):
                raw = match.group(1)
                p = Path(raw)
                if not p.is_absolute():
                    p = Path(project_root) / raw
                if p.exists():
                    include_dirs.add(_norm(p))
            for match in re.finditer(r'(?:-D)([A-Za-z_][A-Za-z0-9_]*(?:=[^\s;&quot;<>]+)?)', text):
                defines.add(match.group(1))
            notes.append(f"Read MPLAB X {file_name} best-effort")
        except Exception as exc:
            notes.append(f"Could not read MPLAB X {file_name}: {exc}")

    return include_dirs, defines, notes


def discover_project(project_root: str) -> ProjectInfo:
    root = _norm(project_root)
    project_type = detect_project_type(root)

    source_files, header_dirs = discover_files_and_header_dirs(root)
    all_header_dirs: set[str] = set(header_dirs)
    all_defines: set[str] = set()
    notes: list[str] = []

    # Always try all known extractors; many projects mix VS Code with vendor IDEs.
    for extractor in (discover_vscode, discover_ti_ccs, discover_mplabx):
        incs, defs, extractor_notes = extractor(root)
        all_header_dirs.update(incs)
        all_defines.update(defs)
        notes.extend(extractor_notes)

    notes.append(f"Generic discovery found {len(source_files)} .c files")
    notes.append(f"Generic discovery found {len(header_dirs)} header folders")

    return ProjectInfo(
        project_root=root,
        project_type=project_type,
        source_files=source_files,
        header_dirs=sorted(all_header_dirs),
        defines=sorted(all_defines),
        notes=notes,
    )
