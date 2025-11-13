import re
from pycparser import CParser, c_ast


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
    Remove preprocessor directive lines such as:
        #include <...>
        #define FOO 123
        #if / #ifdef / #endif etc.

    pycparser expects **preprocessed C** (without raw # directives).
    For ComplyC, we only need the core syntax and structure of the code,
    so it is safe to strip these lines for style / safety checks.
    """
    lines = code.splitlines()
    kept_lines = []

    for line in lines:
        # If the line starts with '#' after optional whitespace, drop it.
        if line.lstrip().startswith("#"):
            continue
        kept_lines.append(line)

    return "\n".join(kept_lines)


def inject_fake_typedefs(code: str) -> str:
    """
    Inject minimal typedefs for common fixed-width types and bool so that
    pycparser can parse code using uint16_t, int32_t, etc. *without* needing
    the real <stdint.h> or <stdbool.h>.

    These typedefs are only for parsing; they don't need to match exact sizes.
    """
    fake_typedefs = """
typedef signed char        int8_t;
typedef unsigned char      uint8_t;
typedef short              int16_t;
typedef unsigned short     uint16_t;
typedef int                int32_t;
typedef unsigned int       uint32_t;
typedef _Bool              bool;
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

    This keeps the logic and structure of the code intact for analysis
    while avoiding constructs pycparser cannot parse directly.
    """
    no_comments = remove_c_comments(code)
    no_pp = remove_preprocessor_directives(no_comments)
    with_typedefs = inject_fake_typedefs(no_pp)
    return with_typedefs


def parse_c_file(path: str) -> c_ast.FileAST:
    """
    Read a C source file, perform light preprocessing, and parse into a pycparser AST.

    Steps:
    - Read the raw .c file.
    - Strip comments and preprocessor directives.
    - Inject minimal typedefs for fixed-width integer types and bool.
    - Parse the cleaned code with CParser.

    Returns:
        pycparser.c_ast.FileAST representing the translation unit.
    """
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    cleaned_code = preprocess_code_for_pycparser(code)

    parser = CParser()
    return parser.parse(cleaned_code, filename=path)
