# ComplyC Stable Build Notes

This build stabilizes the Source Index Engine integration and GUI scan execution.

## Recommended development run
Use:

```bat
RUN_FROM_SOURCE.bat
```

This is the safest workflow while developing.

## Standalone EXE build
Use:

```bat
build_windows_exe.bat
```

The packaged EXE now supports process-worker scan mode by spawning the same EXE
with `--scan-worker`. This avoids the old issue where the GUI could freeze while
GCC preprocessing, pycparser, or rule execution was running.

## Stabilized areas
- Source Index Engine is the single source-location resolver.
- `source_callgraph.py` is now only a compatibility wrapper.
- GUI scan execution uses an external process worker.
- Worker stdout/stderr are written to `reports/complyc_worker_<timestamp>.log`.
- GCC preprocessing has a timeout to avoid indefinite hangs.
- Original source line reporting is preserved for function/global/static naming.
