"""
scan_worker.py - External scan worker for ComplyC GUI.

Runs static analysis outside the Tkinter GUI process so a slow parser/rule path
cannot freeze the desktop UI. The GUI passes a JSON config and receives a JSON
result file.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import traceback
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .loader import load_rules
from .parser import parse_c_file
from .rule_engine import run_rules, Violation
from .reporters import write_json_report, write_html_report, violations_to_dict


def _write_error_reports(failed_files: List[dict], report_dir: Path, timestamp: str) -> Path:
    json_path = report_dir / f"complyc_scan_errors_{timestamp}.json"
    html_path = report_dir / f"complyc_scan_errors_{timestamp}.html"

    payload = {
        "summary": {"failed_files": len(failed_files)},
        "files": failed_files,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='UTF-8'>",
        "<title>ComplyC Scan Error Report</title>",
        """
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
h1, h2 { color: #333; }
table { border-collapse: collapse; width: 100%; margin-top: 16px; }
th, td { border: 1px solid #ccc; padding: 7px 9px; font-size: 14px; vertical-align: top; }
th { background: #f2f2f2; }
.error { color: #b30000; font-weight: bold; }
pre { white-space: pre-wrap; background: #f8f8f8; border: 1px solid #ddd; padding: 8px; }
</style>
""",
        "</head><body>",
        "<h1>ComplyC Scan Error Report</h1>",
        f"<p><b>Failed / skipped files:</b> {len(failed_files)}</p>",
    ]

    if not failed_files:
        parts.append("<p>No scan errors. All selected files were parsed successfully.</p>")
    else:
        parts.append("<table>")
        parts.append("<tr><th>#</th><th>File</th><th>Error Type</th><th>Error</th><th>Traceback</th></tr>")
        for i, item in enumerate(failed_files, start=1):
            parts.append(
                "<tr>"
                f"<td>{i}</td>"
                f"<td>{html.escape(item.get('file', ''))}</td>"
                f"<td class='error'>{html.escape(item.get('error_type', ''))}</td>"
                f"<td><pre>{html.escape(item.get('error', ''))}</pre></td>"
                f"<td><pre>{html.escape(item.get('traceback', ''))}</pre></td>"
                "</tr>"
            )
        parts.append("</table>")

    parts.append("</body></html>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    return html_path


def run_scan_from_config(config: dict) -> dict:
    rules_path = config["rules_path"]
    selected_files = config["selected_files"]
    include_dirs = config.get("include_dirs", [])
    defines = config.get("defines", [])
    use_gcc = bool(config.get("use_gcc", False))
    report_dir = Path(config["report_dir"])
    timestamp = config["timestamp"]

    report_dir.mkdir(parents=True, exist_ok=True)
    _style, rules = load_rules(rules_path)

    per_file_violations: Dict[str, List[Violation]] = {}
    failed_files: List[dict] = []
    severity_counter: Counter[str] = Counter()

    total_files = len(selected_files)
    for index, file_path in enumerate(selected_files, start=1):
        print(f"[ComplyC worker] Scanning {index}/{total_files}: {file_path}", flush=True)
        try:
            ast = parse_c_file(
                file_path,
                use_gcc=use_gcc,
                include_dirs=include_dirs if use_gcc else [],
                defines=defines if use_gcc else [],
            )
            violations = run_rules(ast, rules, file_path)
            per_file_violations[file_path] = violations
            for v in violations:
                severity_counter[(v.severity or "unspecified").lower()] += 1
        except Exception as file_exc:
            failed_files.append({
                "file": file_path,
                "error_type": type(file_exc).__name__,
                "error": str(file_exc),
                "traceback": traceback.format_exc(),
            })

    json_report = report_dir / f"complyc_report_{timestamp}.json"
    html_report = report_dir / f"complyc_report_{timestamp}.html"
    error_report = _write_error_reports(failed_files, report_dir, timestamp)

    write_json_report(per_file_violations, str(json_report))
    write_html_report(per_file_violations, str(html_report))
    data = violations_to_dict(per_file_violations)

    return {
        "ok": True,
        "data": data,
        "failed_files": failed_files,
        "json_report": str(json_report),
        "html_report": str(html_report),
        "error_report": str(error_report),
        "report_dir": str(report_dir),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ComplyC external GUI scan worker")
    ap.add_argument("--config", required=True)
    ap.add_argument("--result", required=True)
    args = ap.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
        result = run_scan_from_config(config)
    except Exception as exc:
        result = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    with open(args.result, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
