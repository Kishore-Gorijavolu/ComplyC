# Stable Verification - v0.2.4

Verification performed before packaging:

```bash
python3 -m compileall -q complyc complyc_gui.py tests/test_source_index_engine.py
python3 tests/test_source_index_engine.py
PYTHONPATH=. python3 -m complyc.main --rules rules/complyc_style.yml --no-gcc --quiet examples/sample_bad.c
PYTHONPATH=. python3 -m complyc.main --rules rules/complyc_style.yml --no-gcc --quiet tests/regression/source_index_fixture.c
PYTHONPATH=. python3 -m complyc.main --rules rules/complyc_style.yml --use-gcc --quiet tests/regression/source_index_fixture.c
```

Confirmed source-indexed report locations:

| Symbol | Expected Line | Result |
|---|---:|---|
| `Tsk_button` | 6 | Pass |
| `button_not_changed_counter` | 4 | Pass |
| `btn_last` | 13 | Pass |

Confirmed behavior:

- Source Index Engine imports and compiles.
- Rule engine imports and compiles.
- GUI source imports and compiles.
- Built-in backend scan completes.
- GCC backend scan completes on regression fixture.
- Macro-expanded constant `MAX_SPEED` is not reported as a raw magic number.
