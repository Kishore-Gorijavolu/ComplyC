from pathlib import Path

from complyc.loader import load_rules
from complyc.parser import parse_c_file
from complyc.rule_engine import run_rules

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "rules" / "complyc_style.yml"
BAD = ROOT / "examples" / "security_pack_v1_bad.c"
GOOD = ROOT / "examples" / "security_pack_v1_good.c"


def _security_ids(path: Path):
    _, rules = load_rules(str(RULES))
    security_rules = [rule for rule in rules if rule["id"].startswith("SEC_")]
    ast = parse_c_file(str(path), use_gcc=False)
    return {v.rule_id for v in run_rules(ast, security_rules, str(path))}


def test_bad_fixture_triggers_core_security_rules():
    found = _security_ids(BAD)
    expected = {
        "SEC_INPUT_GETS_001",
        "SEC_STRING_COPY_002",
        "SEC_FORMAT_WRITE_003",
        "SEC_FORMAT_STRING_004",
        "SEC_SCANF_WIDTH_005",
        "SEC_COMMAND_EXEC_006",
        "SEC_TEMP_FILE_007",
        "SEC_WEAK_RANDOM_008",
        "SEC_HARDCODED_SECRET_010",
        "SEC_ARRAY_BOUNDS_011",
        "SEC_DIV_ZERO_012",
        "SEC_INVALID_SHIFT_013",
        "SEC_ALLOC_OVERFLOW_014",
    }
    assert expected.issubset(found)


def test_good_fixture_has_no_security_findings():
    assert _security_ids(GOOD) == set()
