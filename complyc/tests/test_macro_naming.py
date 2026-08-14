from pathlib import Path

from complyc.parser import parse_c_file
from complyc.rule_engine import run_rules


RULE = {
    "id": "NAMING_MACRO_001",
    "title": "Macros must be UPPER_SNAKE_CASE",
    "scope": "macro",
    "check": "macro_naming",
    "pattern": r"^[A-Z][A-Z0-9_]*$",
    "severity": "minor",
    "guidance": "Use UPPER_SNAKE_CASE for macros.",
    "reference": "Beta regression test",
}


def test_macro_naming_reports_only_invalid_macro(tmp_path: Path):
    source = tmp_path / "macro_sample.c"
    source.write_text(
        "#define GOOD_MACRO 1\n"
        "#define badMacro 2\n"
        "# define ALSO_GOOD(x) ((x) + 1)\n"
        "int main(void) { return GOOD_MACRO; }\n",
        encoding="utf-8",
    )

    ast = parse_c_file(str(source), use_gcc=False)
    violations = run_rules(ast, [RULE], str(source))

    assert len(violations) == 1
    assert violations[0].rule_id == "NAMING_MACRO_001"
    assert violations[0].line == 2
    assert "badMacro" in violations[0].message
