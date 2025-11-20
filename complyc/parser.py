import re
import subprocess
import tempfile
import os
from pycparser import CParser, c_ast


# ============================================================
#   Lightweight Built-in Preprocessing (original behavior)
# ============================================================

def remove_c_comments(code: str) -> str:
    """
    Strip both // line comments and /* ... */ block comments.

    NOTE:
    - This uses a simple regex-based approach.
    - It is not 100% C-standard-perfect (e.g., edge cases with comment-like
      sequences inside string literals), but it is good enough for
      typical embedded C style checking.
    """
    # Matches:
    #   // ... end of line
    #   /* ... block comment ... */
    pattern = r'//.*?$|/\*.*?\*/'
    return re.sub(pattern, '', code, flags=re.MULTILINE | re.DOTALL)


def remove_preprocessor_directives(code: str) -> str:
    """
    Remove lines that start with '#' (preprocessor directives).

    This keeps things simple for pycparser by stripping:
      - #include ...
      - #define ...
      - #if/#ifdef/#ifndef/#else/#endif
      - #pragma ...
    """
    cleaned_lines = []
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # Skip preprocessor lines
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def inject_fake_typedefs(code: str) -> str:
    """
    Inject a small set of typedefs for common fixed-width integer types
    and bool, so that pycparser can parse code that relies on <stdint.h>
    and <stdbool.h> without pulling real system headers (which may use
    non-standard extensions).

    If your project needs more, extend this list as needed.
    """
    fake_typedefs = """
typedef signed char         int8_t;
typedef unsigned char       uint8_t;
typedef short               int16_t;
typedef unsigned short      uint16_t;
typedef int                 int32_t;
typedef unsigned int        uint32_t;
typedef long long           int64_t;
typedef unsigned long long  uint64_t;
typedef _Bool               bool;
"""
    # Put typedefs at the very top so they are visible everywhere.
    return fake_typedefs + "\n" + code


def preprocess_code_for_pycparser(code: str) -> str:
    """
    Apply all lightweight preprocessing steps needed before feeding code into pycparser:

    1. Remove C-style comments (// and /* ... */).
    2. Remove preprocessor directives (lines starting with '#').
    3. Inject fake typedefs for stdint/bool types so pycparser can parse
       code that originally relied on <stdint.h> and <stdbool.h>.
    """
    no_comments = remove_c_comments(code)
    no_pp = remove_preprocessor_directives(no_comments)
    with_typedefs = inject_fake_typedefs(no_pp)
    return with_typedefs


# ============================================================
#   GCC-based Preprocessing (optional mode)
# ============================================================

def preprocess_with_gcc(path: str) -> str:
    """
    Use GCC as a preprocessor on the given source file.

    Command used:
        gcc -E -P <path> -o <temp_file>

    -E : only run the preprocessor
    -P : inhibit linemarkers (#line), which confuse pycparser

    Returns:
        The preprocessed code as a string with injected fake typedefs.
    """
    # Create a temporary file to hold the preprocessed output
    fd, tmp_out_path = tempfile.mkstemp(suffix=".c", prefix="complyc_gcc_")
    os.close(fd)  # We only need the path; gcc will write to it directly.

    cmd = ["gcc", "-E", "-P", "-I", "fake_libc_include", path, "-o", tmp_out_path]

    try:
        # Capture stdout/stderr for debugging if something goes wrong
        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print("[ComplyC] ERROR: gcc not found on system PATH.")
        print("[ComplyC] Hint: Install GCC or remove --use-gcc / set preprocessor: 'builtin'.")
        raise
    except subprocess.CalledProcessError as e:
        print("[ComplyC] GCC preprocessing failed.")
        print("[ComplyC] Command :", " ".join(cmd))
        print("[ComplyC] Stdout  :", e.stdout)
        print("[ComplyC] Stderr  :", e.stderr)
        # Re-raise so the caller can decide how to handle it
        raise

    # Read the preprocessed file
    try:
        with open(tmp_out_path, "r", encoding="utf-8") as f:
            preprocessed_code = f.read()
    finally:
        # Best-effort cleanup of the temporary file
        try:
            os.remove(tmp_out_path)
        except OSError:
            pass

    # Inject minimal typedefs for fixed-width types / bool
    return inject_fake_typedefs(preprocessed_code)


# ============================================================
#   GCC output sanitization for pycparser
# ============================================================

def sanitize_gcc_output_for_pycparser(code: str) -> str:
    """
    Hard sanitize GCC output so pycparser can parse the result reliably.
    This removes ALL GNU/builtin/system-header constructs.
    """

    # Drop ALL lines containing these GNU keywords
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
        r'__label__'
    ]

    for pat in forbidden:
        code = re.sub(rf'^.*{pat}.*$', '', code, flags=re.MULTILINE)

    # Also remove any typedef or struct that starts with __ or _
    code = re.sub(r'^typedef\s+.*__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^struct\s+__.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^union\s+__.*$', '', code, flags=re.MULTILINE)

    # Remove any __attribute__((...)) patterns
    code = re.sub(r'__attribute__\s*\(\([^)]*\)\)', '', code)

    # Remove leftover compiler-specific tokens
    code = re.sub(r'\b__\w+\b', '', code)

    # Remove any line with standalone parenthesis (causes parse errors)
    code = re.sub(r'^\s*\(\s*\)\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*\(\s*$', '', code, flags=re.MULTILINE)

    # Remove empty lines created by filtering
    cleaned_lines = []
    for line in code.splitlines():
        if line.strip() == "":
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


# ============================================================
#   Main entry for parsing C files
# ============================================================

def parse_c_file(path: str, use_gcc: bool = False) -> c_ast.FileAST:
    """
    Read a C source file, preprocess it, and parse into a pycparser AST.

    Parameters:
        path    : Path to a .c file.
        use_gcc : If True, use GCC (-E -P) as a real preprocessor.
                  If False, use the lightweight regex-based preprocessing.

    Steps (lightweight mode):
        - Read the raw .c file.
        - Strip comments and preprocessor directives.
        - Inject minimal typedefs for fixed-width integer types and bool.
        - Parse the cleaned code with CParser.

    Steps (GCC mode):
        - Run 'gcc -E -P' on the file.
        - Inject minimal typedefs.
        - Sanitize GCC-specific constructs (__gnuc_va_list, attributes, etc.).
        - Parse the preprocessed code with CParser.

    Returns:
        pycparser.c_ast.FileAST representing the translation unit.
    """
    if use_gcc:
        cleaned_code = preprocess_with_gcc(path)
        cleaned_code = sanitize_gcc_output_for_pycparser(cleaned_code)
    else:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        cleaned_code = preprocess_code_for_pycparser(code)

    parser = CParser()
    return parser.parse(cleaned_code, filename=path)
