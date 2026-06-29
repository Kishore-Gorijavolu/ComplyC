# Stable Build Verification

Verified in backend before packaging.

## Tests executed

1. Python compile check

```text
python -m compileall -q complyc_gui.py complyc
```

Result: PASS

2. External worker mode through GUI entry point

```text
python complyc_gui.py --scan-worker --config <config.json> --result <result.json>
```

Result: PASS

3. GCC scan on sample files

```text
examples/sample_bad.c
examples/sample_good.c
```

Result: PASS, 2 files parsed, 0 failed files.

4. Source line alignment regression file

Expected mappings:

```text
Tsk_button                       -> line 43
GG_LIN_and_button_sleep_flag     -> line 41
button_not_changed_counter       -> line 35
btn_last                         -> line 73
```

Observed mappings:

```text
Tsk_button                       -> line 43
GG_LIN_and_button_sleep_flag     -> line 41
button_not_changed_counter       -> line 35
btn_last                         -> line 73
```

Result: PASS

## Notes

Use `RUN_FROM_SOURCE.bat` as the stable development runner.
Use `build_windows_exe.bat` only when creating a standalone EXE.
