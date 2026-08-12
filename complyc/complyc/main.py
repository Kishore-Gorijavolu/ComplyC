import argparse
import os
import glob
from collections import Counter
from datetime import datetime

from .loader import load_rules
from .parser import parse_c_file
from .rule_engine import run_rules
from .reporters import write_json_report, write_html_report
from .cfg import build_cfg  # optional debug CFG view only


def ensure_reports_dir() -> str:
    """Ensure the reports/ folder exists and return its path."""
    reports_dir = "reports"
    if not os.path.isdir(reports_dir):
        os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def clean_reports_folder():
    """Delete all files inside reports/ folder (if it exists)."""
    reports_dir = "reports"
    if not os.path.isdir(reports_dir):
        return  # nothing to clean

    for file in glob.glob(os.path.join(reports_dir, "*")):
        try:
            os.remove(file)
        except Exception as e:
            print(f"[ComplyC] Could not delete {file}: {e}")

    print("[ComplyC] Cleaned reports/ folder")


def make_timestamp() -> str:
    """Return a timestamp string like 20251113_153045."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    parser = argparse.ArgumentParser(description="ComplyC – Coding Style Checker")
    parser.add_argument("--rules", required=True, help="Path to YAML rules file")
    parser.add_argument("--json-report", help="Path to write JSON report (optional)")
    parser.add_argument("--html-report", help="Path to write HTML report (optional)")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed per-file violation output (summary only)",
    )
    parser.add_argument(
        "--clean-reports",
        action="store_true",
        help="Delete all existing files inside the reports folder before generating new reports",
    )
    parser.add_argument(
        "--use-gcc",
        action="store_true",
        help="Force use of GCC (-E -P) as a preprocessor (overrides YAML).",
    )
    parser.add_argument(
        "--no-gcc",
        action="store_true",
        help="Force use of builtin regex preprocessor (overrides YAML).",
    )
    parser.add_argument("files", nargs="+", help="C source files to analyze")
    args = parser.parse_args()

    # Load style + rules from YAML
    style, rules = load_rules(args.rules)
    style = style or {}

    # Base mode from YAML
    preproc_mode = str(style.get("preprocessor", "builtin")).lower()

    # Determine preprocessor mode
    if args.use_gcc:
        use_gcc = True
    elif args.no_gcc:
        use_gcc = False
    else:
        use_gcc = (preproc_mode == "gcc")

    print("[ComplyC] Preprocessor mode:",
          "GCC (-E -P)" if use_gcc else "builtin regex stripper")

    per_file_violations = {}
    severity_counter = Counter()
    total_violations = 0

    # ---------- Per-file analysis ----------
    for path in args.files:

        # --- Step 1: Parse AST ---
        ast = parse_c_file(path, use_gcc=use_gcc)

        # --- Step 2 (optional): Build CFGs just for debug view ---
        if not args.quiet:
            cfgs = build_cfg(ast)
            for func_name, cfg in cfgs.items():
                print(f"\n[CFG] Function: {func_name}")
                cfg.dump()
                print(f"  Cyclomatic Complexity = {cfg.compute_cyclomatic_complexity()}\n")

        # --- Step 3: Rule Checking (AST + Dataflow via YAML rules) ---
        violations = run_rules(ast, rules, path)
        per_file_violations[path] = violations

        total_violations += len(violations)
        for v in violations:
            sev = (v.severity or "unspecified").lower()
            severity_counter[sev] += 1

        # --- Step 4: Per-file console output ---
        if not args.quiet:
            print(f"\nFile: {path}")
            if not violations:
                print("  No violations found ✅")
            else:
                for v in violations:
                    line = f"line {v.line}" if v.line is not None else "line ?"
                    print(f"  [{v.rule_id}] {line}: {v.message}")

    # ---------- Summary ----------
    print("\n==================== Summary ====================")
    print(f"Total files analyzed   : {len(per_file_violations)}")
    print(f"Total violations found : {total_violations}")

    if total_violations == 0:
        print("Overall status         : ✅ Clean (no violations)")
    else:
        print("Overall status         : ⚠️ Issues detected")
        print("Violations by severity :")
        for sev, count in sorted(severity_counter.items()):
            label = sev.capitalize()
            print(f"  - {label:11} : {count}")

    print("=================================================\n")

    # ---------- Reports (JSON / HTML) ----------
    reports_dir = ensure_reports_dir()

    if args.clean_reports:
        clean_reports_folder()

    ts = make_timestamp()

    # Build short filename tag
    file_basenames = [os.path.splitext(os.path.basename(f))[0] for f in args.files]
    file_tag = file_basenames[0] if len(file_basenames) == 1 else "_And_".join(file_basenames)

    # Use provided paths or auto-generate
    json_path = args.json_report
    html_path = args.html_report

    if json_path is None and html_path is None:
        json_path = os.path.join(reports_dir, f"complyc_report_{file_tag}_{ts}.json")
        html_path = os.path.join(reports_dir, f"complyc_report_{file_tag}_{ts}.html")

    if json_path:
        write_json_report(per_file_violations, json_path)

    if html_path:
        write_html_report(per_file_violations, html_path, rules=rules)


if __name__ == "__main__":
    main()
