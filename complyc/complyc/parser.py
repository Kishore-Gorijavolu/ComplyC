import re
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from pycparser import CParser, c_ast


# ============================================================
#   GCC source mapping support
# ============================================================

# Maps analyzed translation-unit path -> {preprocessed_line: (original_file, original_line)}
_LAST_GCC_SOURCE_MAPS: Dict[str, Dict[int, Tuple[str, int]]] = {}


def _norm_path(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def build_gcc_source_map(preprocessed_code: str, fallback_file: str) -> Dict[int, Tuple[str, int]]:
    """
    Build a line map from GCC preprocessor output.

    GCC emits directives like:
        # 1 "C:/project/src/button.c"
        # 25 "C:/project/src/button.h" 1

    The directive applies to the *next* physical output line. This map lets
    ComplyC translate pycparser/preprocessed line numbers back to the original
    source file and source line.
    """
    source_map: Dict[int, Tuple[str, int]] = {}
    current_file = os.path.abspath(fallback_file)
    current_line = 1

    line_directive_re = re.compile(r'^\s*#\s+(\d+)\s+"([^"]+)"')

    for pp_line_no, line in enumerate(preprocessed_code.splitlines(), start=1):
        match = line_directive_re.match(line)
        if match:
            current_line = int(match.group(1))
            current_file = match.group(2)
            if not current_file.startswith("<") and not os.path.isabs(current_file):
                current_file = os.path.abspath(current_file)
            source_map[pp_line_no] = (current_file, current_line)
            continue

        source_map[pp_line_no] = (current_file, current_line)
        current_line += 1

    return source_map


def get_mapped_source_location(translation_unit_path: str, preprocessed_line: Optional[int]) -> Optional[Tuple[str, int]]:
    """Return (original_file, original_line) for a pycparser/preprocessed line."""
    if preprocessed_line is None:
        return None
    source_map = _LAST_GCC_SOURCE_MAPS.get(_norm_path(translation_unit_path))
    if not source_map:
        return None
    return source_map.get(int(preprocessed_line))


# ============================================================
#   Lightweight Built-in Preprocessing
# ============================================================

def remove_c_comments(code: str) -> str:
    pattern = r'//.*?$|/\*.*?\*/'
    return re.sub(pattern, '', code, flags=re.MULTILINE | re.DOTALL)


def remove_preprocessor_directives(code: str) -> str:
    cleaned_lines = []
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def inject_fake_typedefs(code: str) -> str:
    fake_typedefs = r"""
typedef signed char         int8_t;
typedef unsigned char       uint8_t;
typedef short               int16_t;
typedef unsigned short      uint16_t;
typedef int                 int32_t;
typedef unsigned int        uint32_t;
typedef long long           int64_t;
typedef unsigned long long  uint64_t;
typedef signed char         sint8;
typedef unsigned char       uint8;
typedef short               sint16;
typedef unsigned short      uint16;
typedef int                 sint32;
typedef unsigned int        uint32;
typedef float               float32;
typedef double              float64;
typedef unsigned char       boolean;
typedef _Bool               bool;
"""
    return fake_typedefs + "\n" + code


def preprocess_code_for_pycparser(code: str) -> str:
    no_comments = remove_c_comments(code)
    no_pp = remove_preprocessor_directives(no_comments)
    return inject_fake_typedefs(no_pp)


# ============================================================
#   GCC-based Preprocessing
# ============================================================

def get_resource_path(relative_path: str) -> str:
    """Resolve resource path for source execution and PyInstaller onefile EXE."""
    import sys

    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, relative_path)


def _normalize_define(define: str) -> str:
    define = str(define).strip()
    if not define:
        return ""
    if define.startswith("-D"):
        return define
    return "-D" + define


def preprocess_with_gcc(
    path: str,
    include_dirs: Optional[Iterable[str]] = None,
    defines: Optional[Iterable[str]] = None,
    gcc_path: str = "gcc",
) -> str:
    """
    Use GCC as a preprocessor with bundled fake headers plus project include paths.

    - -E: preprocessing only
    - GCC #line markers are mapped first, then blanked before pycparser
    - -nostdinc: do not scan host/system headers
    - fake_libc_include: bundled lightweight headers for parsing
    - include_dirs: project/vendor include folders discovered by ComplyC
    - defines: project macros such as UNIT_TEST, STD_ON=1, CPU_XYZ
    """
    fd, tmp_out_path = tempfile.mkstemp(suffix=".c", prefix="complyc_gcc_")
    os.close(fd)

    fake_include_path = get_resource_path("fake_libc_include")

    cmd: List[str] = [
        gcc_path,
        "-E",
        "-nostdinc",
        "-I", fake_include_path,
    ]

    for inc in include_dirs or []:
        if inc and os.path.isdir(str(inc)):
            cmd.extend(["-I", str(inc)])

    for define in defines or []:
        normalized = _normalize_define(str(define))
        if normalized:
            cmd.append(normalized)

    cmd.extend([path, "-o", tmp_out_path])

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "gcc.exe was not found. Install MinGW-w64 or add gcc.exe to PATH."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "GCC preprocessing failed.\n\n"
            "Common causes:\n"
            "1. Missing project include folder.\n"
            "2. Missing fake header for a vendor/AUTOSAR header.\n"
            "3. Missing compiler macro/define.\n"
            "4. Source file depends on compiler-specific syntax.\n\n"
            "Command:\n"
            + " ".join(cmd)
            + "\n\nGCC stderr:\n"
            + (e.stderr or "")
        ) from e

    try:
        with open(tmp_out_path, "r", encoding="utf-8", errors="ignore") as f:
            preprocessed_code = f.read()
    finally:
        try:
            os.remove(tmp_out_path)
        except OSError:
            pass

    _LAST_GCC_SOURCE_MAPS[_norm_path(path)] = build_gcc_source_map(preprocessed_code, path)

    # In GCC mode, project/fake headers should provide needed typedefs.
    # Do not inject extra typedef lines here because that shifts pycparser coordinates.
    return preprocessed_code


def remove_line_markers_keep_line_count(code: str) -> str:
    """
    Remove GCC #line marker lines but keep blank lines in their place.

    pycparser cannot parse GCC line directives, but replacing each marker
    with a blank line preserves the physical preprocessed line numbers used
    by the source map.
    """
    cleaned_lines = []

    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("# ") or stripped.startswith("#line"):
            cleaned_lines.append("")
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# ============================================================
#   GCC output sanitization for pycparser
# ============================================================

def sanitize_gcc_output_for_pycparser(code: str) -> str:
    forbidden = [
        r'__gnuc_va_list',
        r'__builtin_va_list',
        r'__builtin_',
        r'__va_list_tag',
        r'__asm__',
        r'__asm',
        r'__inline__',
        r'__inline',
        r'__attribute__',
        r'__extension__',
        r'__restrict__',
        r'__restrict',
        r'__typeof__',
        r'__label__',
        r'__interrupt',
        r'__cregister',
    ]

    for pat in forbidden:
        code = re.sub(rf'^.*{pat}.*$', '', code, flags=re.MULTILINE)

    code = re.sub(r'^typedef\s+.*__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^struct\s+__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^union\s+__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'__attribute__\s*\(\([^)]*\)\)', '', code)
    code = re.sub(r'\b__\w+\b', '', code)
    code = re.sub(r'^\s*\(\s*\)\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*\(\s*$', '', code, flags=re.MULTILINE)

    # cleaned_lines = []
    # for line in code.splitlines():
    #     if line.strip() == "":
    #         continue
    #     cleaned_lines.append(line)
    # return "\n".join(cleaned_lines)
    return code


# ============================================================
#   Main entry for parsing C files
# ============================================================

def parse_c_file(
    path: str,
    use_gcc: bool = False,
    include_dirs: Optional[Iterable[str]] = None,
    defines: Optional[Iterable[str]] = None,
    gcc_path: str = "gcc",
) -> c_ast.FileAST:
    """
    Read a C source file, preprocess it, and parse into pycparser AST.

    For embedded projects, use_gcc=True with include_dirs and defines discovered
    from the project root.
    """
    if use_gcc:
        cleaned_code = preprocess_with_gcc(
            path,
            include_dirs=include_dirs,
            defines=defines,
            gcc_path=gcc_path,
        )
        cleaned_code = remove_line_markers_keep_line_count(cleaned_code)
        cleaned_code = sanitize_gcc_output_for_pycparser(cleaned_code)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        cleaned_code = preprocess_code_for_pycparser(code)

    parser = CParser()
    return parser.parse(cleaned_code, filename=path)
