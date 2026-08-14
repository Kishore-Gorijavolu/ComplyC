import re
import sys
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from pycparser import CParser, c_ast

from .compiler_extensions import sanitize_compiler_extensions
from .type_recovery import apply_type_recovery


# ============================================================
#   GCC source mapping support
# ============================================================

# Maps analyzed translation-unit path -> {preprocessed_line: (original_file, original_line)}
_LAST_GCC_SOURCE_MAPS: Dict[str, Dict[int, Tuple[str, int]]] = {}

# Number of synthetic typedef lines injected before pycparser sees the text.
# Used to compensate source mapping in GCC mode.
_LAST_SYNTHETIC_LINE_OFFSETS: Dict[str, int] = {}

# Last preprocessing status for diagnostics/reporting. Existing callers do not
# depend on this; it is additive and safe for Community Edition integrations.
_LAST_PREPROCESS_STATUS: Dict[str, Dict[str, object]] = {}

# Scan-session header index cache: root -> basename -> absolute header paths.
# This avoids repeated os.walk() calls when many translation units reference
# the same SDK/vendor tree.
_HEADER_INDEX_CACHE: Dict[str, Dict[str, List[str]]] = {}


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
    key = _norm_path(translation_unit_path)
    source_map = _LAST_GCC_SOURCE_MAPS.get(key)
    if not source_map:
        return None

    adjusted_line = int(preprocessed_line) - _LAST_SYNTHETIC_LINE_OFFSETS.get(key, 0)
    if adjusted_line < 1:
        return None
    return source_map.get(adjusted_line)


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
    return sanitize_compiler_extensions(inject_fake_typedefs(no_pp))


# ============================================================
#   GCC-based Preprocessing
# ============================================================


# ============================================================
#   GCC preprocessing recovery support
# ============================================================

_MISSING_HEADER_RE = re.compile(
    r"fatal error:\s*([^\r\n:]+(?:[\\/][^\r\n:]+)*\.(?:h|hpp|hh))\s*:\s*No such file or directory",
    re.IGNORECASE,
)

_COMPILER_NOT_SUPPORTED_RE = re.compile(
    r'error:\s*#error\s+["<]?(?:compiler\s+not\s+supported|unsupported\s+compiler|unknown\s+compiler)',
    re.IGNORECASE,
)

_COMPILER_ERROR_LINE_RE = re.compile(
    r'^\s*#\s*error\b.*(?:compiler\s+not\s+supported|unsupported\s+compiler|unknown\s+compiler).*$',
    re.IGNORECASE | re.MULTILINE,
)

# Avoid walking enormous roots such as C:\\ or /. A project root below this
# depth is considered too broad for automatic recursive recovery.
_MIN_SEARCH_ROOT_PARTS = 2
_MAX_HEADER_RECOVERY_RETRIES = 32


def _extract_missing_header(stderr: str) -> Optional[str]:
    """Extract a missing header path from GCC stderr, if present."""
    if not stderr:
        return None
    match = _MISSING_HEADER_RE.search(stderr)
    if not match:
        return None
    return match.group(1).strip().strip('"<>').replace("\\", "/")


def _stderr_is_compiler_guard_failure(stderr: str) -> bool:
    return bool(stderr and _COMPILER_NOT_SUPPORTED_RE.search(stderr))


def _derive_include_root_from_header_dirs(
    missing_header: str,
    include_dirs: Iterable[str],
) -> Optional[str]:
    """Derive the correct -I root when discovery supplied the leaf directory."""
    requested = Path(missing_header.replace("\\", "/"))
    parts = requested.parts
    if not parts:
        return None

    basename = parts[-1]
    matches: List[str] = []

    for inc in include_dirs or []:
        if not inc:
            continue
        header_path = Path(str(inc)) / basename
        if not header_path.is_file():
            continue

        try:
            resolved = header_path.resolve()
        except OSError:
            continue
        header_parts = resolved.parts
        if len(header_parts) < len(parts):
            continue

        tail = header_parts[-len(parts):]
        if tuple(os.path.normcase(x) for x in tail) != tuple(os.path.normcase(x) for x in parts):
            continue

        root = resolved
        for _ in parts:
            root = root.parent
        matches.append(str(root))

    unique_matches = sorted({_norm_path(m) for m in matches})
    if len(unique_matches) == 1:
        return unique_matches[0]
    return None


def _candidate_project_search_roots(source_path: str, include_dirs: Iterable[str]) -> List[str]:
    """Infer bounded project roots without requiring a new public API parameter."""
    source_parent = Path(source_path).resolve().parent
    existing_dirs = [Path(str(x)).resolve() for x in (include_dirs or []) if x and Path(str(x)).is_dir()]

    candidates: List[Path] = []
    if existing_dirs:
        try:
            common = Path(os.path.commonpath([str(source_parent)] + [str(x) for x in existing_dirs]))
            if len(common.parts) >= _MIN_SEARCH_ROOT_PARTS:
                candidates.append(common)
        except (ValueError, OSError):
            pass

    # Source parent is always safe and cheap. Parent/grandparent improve recovery
    # for projects where only one module's header directories were discovered.
    for candidate in (source_parent, source_parent.parent):
        if len(candidate.parts) >= _MIN_SEARCH_ROOT_PARTS:
            candidates.append(candidate)

    unique: List[str] = []
    seen: Set[str] = set()
    for candidate in candidates:
        norm = _norm_path(str(candidate))
        if norm in seen or not candidate.is_dir():
            continue
        seen.add(norm)
        unique.append(str(candidate))
    return unique


def _build_header_index(root: str) -> Dict[str, List[str]]:
    """Build/cache a basename index for one bounded project root."""
    norm_root = _norm_path(root)
    cached = _HEADER_INDEX_CACHE.get(norm_root)
    if cached is not None:
        return cached

    index: Dict[str, List[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in {'.git', '.svn', '.hg', '__pycache__', 'node_modules', 'build', 'out', 'dist'}
        ]
        for filename in filenames:
            if Path(filename).suffix.lower() not in {'.h', '.hpp', '.hh'}:
                continue
            index.setdefault(os.path.normcase(filename), []).append(str(Path(dirpath) / filename))

    _HEADER_INDEX_CACHE[norm_root] = index
    return index


def _find_header_include_root_recursively(
    missing_header: str,
    source_path: str,
    include_dirs: Iterable[str],
) -> Optional[str]:
    """Search cached, bounded project indexes for an exact requested suffix."""
    requested = Path(missing_header.replace("\\", "/"))
    parts = requested.parts
    if not parts:
        return None

    basename_key = os.path.normcase(parts[-1])
    matches: Set[str] = set()

    for root in _candidate_project_search_roots(source_path, include_dirs):
        index = _build_header_index(root)
        for candidate_text in index.get(basename_key, []):
            candidate = Path(candidate_text)
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if len(resolved.parts) < len(parts):
                continue
            tail = resolved.parts[-len(parts):]
            if tuple(os.path.normcase(x) for x in tail) != tuple(os.path.normcase(x) for x in parts):
                continue

            include_root = resolved
            for _ in parts:
                include_root = include_root.parent
            matches.add(_norm_path(str(include_root)))
            if len(matches) > 1:
                return None  # Ambiguous SDK/header variant: never guess.

    return next(iter(matches)) if len(matches) == 1 else None


def _create_fake_header_alias(
    missing_header: str,
    fake_include_path: str,
    virtual_include_root: str,
) -> bool:
    """Create a nested alias to an existing bundled same-basename fake header."""
    normalized = missing_header.replace("\\", "/").lstrip("/")
    requested = Path(normalized)
    if not requested.parts or ".." in requested.parts:
        return False

    bundled = Path(fake_include_path) / requested.name
    if not bundled.is_file():
        return False

    target = Path(virtual_include_root).joinpath(*requested.parts)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"#include <{requested.name}>\n", encoding="utf-8")
        return True
    except OSError:
        return False


def _create_opaque_vendor_header(missing_header: str, virtual_include_root: str) -> bool:
    """
    Create an empty compatibility header only for nested vendor/project includes.

    This is intentionally a last-resort GCC recovery step. It does not fake
    symbols or types; it merely lets GCC continue so ComplyC's existing type
    recovery can analyze source-level rules. Flat/standard-looking headers are
    not auto-created, preventing accidental masking of missing libc headers.
    """
    normalized = missing_header.replace("\\", "/").lstrip("/")
    requested = Path(normalized)
    if len(requested.parts) < 2 or ".." in requested.parts:
        return False
    if requested.suffix.lower() not in {".h", ".hpp", ".hh"}:
        return False

    target = Path(virtual_include_root).joinpath(*requested.parts)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "/* ComplyC analysis-only opaque compatibility header. */\n#pragma once\n",
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def _looks_like_ti_embedded_project(source_path: str) -> bool:
    """Detect TI/MSP usage from source includes without vendor-specific setup UI."""
    try:
        text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return bool(re.search(r'#\s*include\s*[<"]ti[\\/]', text, flags=re.IGNORECASE))


def _compiler_profile_defines(source_path: str) -> List[str]:
    """Return conservative host-GCC defines for known embedded compiler guards."""
    if _looks_like_ti_embedded_project(source_path):
        # Do not define TI compiler macros: that can select TI-only syntax.
        # Instead select the GCC/ARM branch that vendor startup code typically
        # exposes while keeping actual preprocessing under GCC.
        return ["__arm__=1", "__thumb__=1", "__ARM_ARCH_6M__=1", "__ARM_ARCH=6"]
    return []


def _create_compiler_guard_relaxed_source(source_path: str, temp_dir: str) -> Optional[str]:
    """
    Create a line-preserving temporary source that neutralizes only explicit
    'compiler not supported' #error directives in the translation unit itself.
    Other #error directives remain untouched.
    """
    try:
        original = Path(source_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    changed = False
    lines: List[str] = []
    for line in original.splitlines(keepends=True):
        if _COMPILER_ERROR_LINE_RE.match(line):
            newline = "\n" if line.endswith("\n") else ""
            lines.append("/* ComplyC: compiler guard relaxed for static analysis */" + newline)
            changed = True
        else:
            lines.append(line)

    if not changed:
        return None

    target = Path(temp_dir) / Path(source_path).name
    # #line makes GCC's subsequent source markers refer back to the original file.
    content = f'#line 1 "{str(Path(source_path).resolve()).replace(chr(92), "/")}"\n' + ''.join(lines)
    target.write_text(content, encoding="utf-8")
    return str(target)


def _run_gcc_preprocessor(cmd: List[str]) -> None:
    """Run GCC using the same platform/timeout behaviour as legacy preprocessing."""
    run_kwargs = {
        "check": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "timeout": 30,
    }
    if sys.platform.startswith("win"):
        run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.run(cmd, **run_kwargs)


def get_preprocess_status(path: str) -> Dict[str, object]:
    """Return additive diagnostics for the most recent preprocessing of *path*."""
    return dict(_LAST_PREPROCESS_STATUS.get(_norm_path(path), {}))


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
    Use GCC as a preprocessor with adaptive, conservative recovery.

    Recovery order (only after the unchanged normal GCC attempt fails):
      1. Derive an include root from already-discovered header directories.
      2. Recursively search bounded project roots for the exact requested path.
      3. Alias to an existing bundled same-basename compatibility header.
      4. For nested vendor/project headers only, create an analysis-only opaque
         header so GCC can continue and expose the next dependency.
      5. For explicit "compiler not supported" guards, try a conservative
         GCC/ARM static-analysis profile and, if necessary, neutralize only that
         guard in a temporary line-mapped copy of the source.

    The user project is never modified. Existing successful preprocessing takes
    exactly the legacy path and therefore retains current behaviour.
    """
    fd, tmp_out_path = tempfile.mkstemp(suffix=".c", prefix="complyc_gcc_")
    os.close(fd)

    fake_include_path = get_resource_path("fake_libc_include")
    base_include_dirs = [str(inc) for inc in (include_dirs or []) if inc and os.path.isdir(str(inc))]
    user_defines = [str(x) for x in (defines or []) if str(x).strip()]
    source_for_gcc = path

    status: Dict[str, object] = {
        "mode": "gcc",
        "recovered": False,
        "degraded": False,
        "recovered_headers": [],
        "opaque_headers": [],
        "derived_include_roots": [],
        "compiler_guard_relaxed": False,
    }

    def build_cmd(
        extra_include_dirs: Optional[Iterable[str]] = None,
        virtual_root: Optional[str] = None,
        extra_defines: Optional[Iterable[str]] = None,
        source_override: Optional[str] = None,
    ) -> List[str]:
        cmd: List[str] = [gcc_path, "-E", "-nostdinc"]

        if virtual_root:
            cmd.extend(["-I", virtual_root])

        cmd.extend(["-I", fake_include_path])

        seen = set()
        for inc in list(extra_include_dirs or []) + base_include_dirs:
            norm = _norm_path(inc)
            if norm in seen:
                continue
            seen.add(norm)
            cmd.extend(["-I", inc])

        # Preserve quoted-include behaviour when preprocessing a temporary copy.
        source_input = source_override or source_for_gcc
        if source_override:
            source_parent = str(Path(path).resolve().parent)
            if _norm_path(source_parent) not in seen:
                cmd.extend(["-I", source_parent])

        all_defines = user_defines + list(extra_defines or [])
        define_seen = set()
        for define in all_defines:
            normalized = _normalize_define(str(define))
            if normalized and normalized not in define_seen:
                define_seen.add(normalized)
                cmd.append(normalized)

        cmd.extend([source_input, "-o", tmp_out_path])
        return cmd

    cmd = build_cmd()
    last_error: Optional[subprocess.CalledProcessError] = None

    try:
        try:
            _run_gcc_preprocessor(cmd)
        except subprocess.CalledProcessError as first_error:
            last_error = first_error

            with tempfile.TemporaryDirectory(prefix="complyc_headers_") as recovery_root:
                virtual_root = str(Path(recovery_root) / "virtual_include")
                relaxed_root = str(Path(recovery_root) / "relaxed_source")
                Path(virtual_root).mkdir(parents=True, exist_ok=True)
                Path(relaxed_root).mkdir(parents=True, exist_ok=True)

                recovered_roots: List[str] = []
                recovered_headers: Set[str] = set()
                opaque_headers: Set[str] = set()
                extra_profile_defines: List[str] = []
                relaxed_source: Optional[str] = None
                compiler_profile_attempted = False
                compiler_guard_relax_attempted = False

                for _ in range(_MAX_HEADER_RECOVERY_RETRIES):
                    stderr = last_error.stderr or ""
                    missing_header = _extract_missing_header(stderr)

                    if missing_header:
                        # If this header was already recovered and GCC still says it
                        # is missing, recovery cannot make further progress.
                        if missing_header in recovered_headers:
                            raise last_error

                        recovered = False
                        derived_root = _derive_include_root_from_header_dirs(
                            missing_header, base_include_dirs
                        )
                        if not derived_root:
                            derived_root = _find_header_include_root_recursively(
                                missing_header, path, base_include_dirs
                            )

                        if derived_root:
                            norm_root = _norm_path(derived_root)
                            if norm_root not in {_norm_path(x) for x in recovered_roots}:
                                recovered_roots.append(derived_root)
                                cast_list = status["derived_include_roots"]
                                if isinstance(cast_list, list):
                                    cast_list.append(derived_root)
                                recovered = True

                        if not recovered and _create_fake_header_alias(
                            missing_header, fake_include_path, virtual_root
                        ):
                            recovered = True

                        if not recovered and _create_opaque_vendor_header(
                            missing_header, virtual_root
                        ):
                            opaque_headers.add(missing_header)
                            cast_list = status["opaque_headers"]
                            if isinstance(cast_list, list):
                                cast_list.append(missing_header)
                            status["degraded"] = True
                            recovered = True

                        if not recovered:
                            raise last_error

                        recovered_headers.add(missing_header)
                        cast_list = status["recovered_headers"]
                        if isinstance(cast_list, list):
                            cast_list.append(missing_header)
                        status["recovered"] = True

                    elif _stderr_is_compiler_guard_failure(stderr):
                        if not compiler_profile_attempted:
                            compiler_profile_attempted = True
                            profile = _compiler_profile_defines(path)
                            if profile:
                                extra_profile_defines.extend(profile)
                                status["recovered"] = True
                            else:
                                # No known safe profile. Continue to narrow guard
                                # relaxation rather than inventing vendor macros.
                                pass
                        elif not compiler_guard_relax_attempted:
                            compiler_guard_relax_attempted = True
                            relaxed_source = _create_compiler_guard_relaxed_source(path, relaxed_root)
                            if relaxed_source:
                                status["compiler_guard_relaxed"] = True
                                status["recovered"] = True
                                status["degraded"] = True
                            else:
                                raise last_error
                        else:
                            raise last_error
                    else:
                        raise last_error

                    cmd = build_cmd(
                        recovered_roots,
                        virtual_root,
                        extra_profile_defines,
                        relaxed_source,
                    )
                    try:
                        _run_gcc_preprocessor(cmd)
                        last_error = None
                        break
                    except subprocess.CalledProcessError as retry_error:
                        last_error = retry_error
                else:
                    if last_error is not None:
                        raise last_error

                if last_error is not None:
                    raise last_error

    except FileNotFoundError:
        _LAST_PREPROCESS_STATUS[_norm_path(path)] = status
        raise RuntimeError(
            "gcc.exe was not found. Install MinGW-w64 or add gcc.exe to PATH."
        )
    except subprocess.TimeoutExpired as e:
        _LAST_PREPROCESS_STATUS[_norm_path(path)] = status
        raise RuntimeError(
            "GCC preprocessing timed out after 30 seconds.\n\n"
            "This usually means GCC is stuck processing project includes, recursive macros, "
            "or a very large generated header.\n\n"
            "Try:\n"
            "1. Remove unnecessary include folders.\n"
            "2. Disable auto-detected include folders and add only required paths.\n"
            "3. Add missing compiler defines.\n"
            "4. Run Built-in Demo mode for lightweight scans.\n\n"
            "Command:\n"
            + " ".join(cmd)
        ) from e
    except subprocess.CalledProcessError as e:
        _LAST_PREPROCESS_STATUS[_norm_path(path)] = status
        raise RuntimeError(
            "GCC preprocessing failed.\n\n"
            "ComplyC automatically tried project-header discovery, compatibility-header "
            "recovery, and safe compiler-guard recovery before failing.\n\n"
            "Common causes:\n"
            "1. A required SDK is not present anywhere in/near the selected project.\n"
            "2. The missing header is a flat/system header that ComplyC will not fabricate.\n"
            "3. The source requires target-specific compiler syntax rather than preprocessing only.\n"
            "4. A deliberate project #error (other than compiler-not-supported) was triggered.\n\n"
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
    _LAST_PREPROCESS_STATUS[_norm_path(path)] = status
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
    """
    Sanitize GCC/preprocessor output before sending it to pycparser.

    Compiler-specific syntax is delegated to compiler_extensions.py so parser.py
    remains focused on preprocessing, source mapping, and AST construction.
    """
    # Remove/normalize compiler extensions while preserving surrounding C syntax.
    code = sanitize_compiler_extensions(code)

    # Drop pycparser-hostile generated/internal declarations that are not useful
    # for ComplyC coding-guideline analysis. Keep these line-based removals narrow
    # and avoid deleting user functions just because they had an attribute.
    forbidden_line_patterns = [
        r'__gnuc_va_list',
        r'__builtin_va_list',
        r'__builtin_',
        r'__va_list_tag',
    ]

    for pat in forbidden_line_patterns:
        code = re.sub(rf'^.*{pat}.*$', '', code, flags=re.MULTILINE)

    code = re.sub(r'^typedef\s+.*__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^struct\s+__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^union\s+__.*$', '', code, flags=re.MULTILINE)

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

    In GCC mode, Phase 2 recovery is transparent. If GCC recovery made genuine
    progress but ultimately cannot finish, ComplyC makes one lightweight
    analysis fallback attempt. A deliberate/unrecovered GCC failure still
    behaves exactly as before and is reported to the caller.
    """
    key = _norm_path(path)
    _LAST_SYNTHETIC_LINE_OFFSETS[key] = 0
    original_gcc_error: Optional[RuntimeError] = None

    if use_gcc:
        try:
            cleaned_code = preprocess_with_gcc(
                path,
                include_dirs=include_dirs,
                defines=defines,
                gcc_path=gcc_path,
            )
            cleaned_code = remove_line_markers_keep_line_count(cleaned_code)
            cleaned_code = sanitize_gcc_output_for_pycparser(cleaned_code)
        except RuntimeError as exc:
            status = get_preprocess_status(path)
            # Only fallback after a recovery path actually made progress. This
            # prevents ComplyC from hiding a normal compiler/configuration error.
            if not bool(status.get("recovered") or status.get("degraded")):
                raise
            original_gcc_error = exc
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            cleaned_code = preprocess_code_for_pycparser(code)
            status["mode"] = "lightweight-fallback"
            status["degraded"] = True
            _LAST_PREPROCESS_STATUS[key] = status
            _LAST_GCC_SOURCE_MAPS.pop(key, None)
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        cleaned_code = preprocess_code_for_pycparser(code)
        _LAST_PREPROCESS_STATUS[key] = {
            "mode": "builtin",
            "recovered": False,
            "degraded": False,
        }

    # Type Recovery Engine: infer missing project/vendor typedefs and inject
    # harmless placeholders before parsing. This dramatically reduces skipped
    # files in embedded projects that use generated/custom types.
    recovery = apply_type_recovery(cleaned_code)
    cleaned_code = recovery.code
    _LAST_SYNTHETIC_LINE_OFFSETS[key] = recovery.injected_line_count

    parser = CParser()
    try:
        return parser.parse(cleaned_code, filename=path)
    except Exception:
        # When the lightweight fallback cannot produce a valid AST, report the
        # original GCC reason because it is the actionable project dependency.
        if original_gcc_error is not None:
            raise original_gcc_error
        raise

