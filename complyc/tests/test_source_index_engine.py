from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from complyc.source_index_engine import clear_source_index_cache, get_source_index


def test_source_index_fixture_locations():
    clear_source_index_cache()
    fixture = ROOT / "tests" / "regression" / "source_index_fixture.c"
    idx = get_source_index(str(fixture))

    assert idx.find_function("Tsk_button").line == 6
    assert idx.find_function("get_button_is_pressed").line == 11
    assert idx.find_declaration("button_not_changed_counter").line == 4
    assert idx.find_declaration("btn_last").line == 13
    assert idx.find_declaration("btn_now").line == 14
    assert idx.find_macro("MAX_SPEED").line == 2
    assert idx.find_numeric_literal("0", preferred_line=4).line == 4
    assert idx.find_numeric_literal("100", preferred_line=8) is None
    assert idx.find_numeric_literal("0", preferred_line=15).line == 15


if __name__ == "__main__":
    test_source_index_fixture_locations()
    print("Source Index Engine regression tests passed")
