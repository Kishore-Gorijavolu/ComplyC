"""
reporters.py – JSON and HTML report generators for ComplyC
"""

from __future__ import annotations

import json
import html
from dataclasses import asdict
from typing import Dict, List

from .rule_engine import Violation


def violations_to_dict(per_file: Dict[str, List[Violation]]):
    """Convert violations to a JSON-serializable structure."""
    data = {
        "files": [],
        "summary": {
            "total_files": len(per_file),
            "total_violations": 0,
            "by_severity": {},
        },
    }

    total_violations = 0
    severity_count = {}

    for file_path, violations in per_file.items():
        file_entry = {
            "file": file_path,
            "violations": [],
        }
        for v in violations:
            v_dict = asdict(v)
            file_entry["violations"].append(v_dict)

            total_violations += 1
            sev = v.severity or "unspecified"
            severity_count[sev] = severity_count.get(sev, 0) + 1

        data["files"].append(file_entry)

    data["summary"]["total_violations"] = total_violations
    data["summary"]["by_severity"] = severity_count

    return data


def write_json_report(per_file: Dict[str, List[Violation]], outfile: str):
    """Write a JSON report to outfile."""
    data = violations_to_dict(per_file)
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[ComplyC] JSON report written to {outfile}")


def write_html_report(per_file: Dict[str, List[Violation]], outfile: str):
    """Write a simple but clean HTML report."""
    data = violations_to_dict(per_file)

    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html><head><meta charset='UTF-8'>")
    html_parts.append("<title>ComplyC Report</title>")
    html_parts.append("""
<style>
body { font-family: Arial, sans-serif; margin: 20px; }
h1, h2 { color: #333; }
.summary-table, .violations-table {
  border-collapse: collapse;
  margin-bottom: 20px;
  width: 100%;
}
.summary-table th, .summary-table td,
.violations-table th, .violations-table td {
  border: 1px solid #ccc;
  padding: 6px 8px;
  font-size: 14px;
}
.violations-table th {
  background-color: #f2f2f2;
}
.severity-critical { color: #b30000; font-weight: bold; }
.severity-major { color: #cc6600; font-weight: bold; }
.severity-minor { color: #666600; }
.severity-unspecified { color: #555; }
.file-header { background: #e9f0fb; padding: 8px; margin-top: 20px; border-left: 4px solid #4a78c2; }
</style>
""")
    html_parts.append("</head><body>")

    html_parts.append("<h1>ComplyC – Coding Style Report</h1>")

    # Summary section
    s = data["summary"]
    html_parts.append("<h2>Summary</h2>")
    html_parts.append("<table class='summary-table'>")
    html_parts.append("<tr><th>Total files</th><td>{}</td></tr>".format(s["total_files"]))
    html_parts.append("<tr><th>Total violations</th><td>{}</td></tr>".format(s["total_violations"]))
    html_parts.append("<tr><th>Violations by severity</th><td><ul>")
    for sev, count in s["by_severity"].items():
        cls = f"severity-{sev.lower()}"
        html_parts.append(f"<li class='{cls}'>{html.escape(sev)}: {count}</li>")
    html_parts.append("</ul></td></tr>")
    html_parts.append("</table>")

    # Per-file section
    for file_entry in data["files"]:
        file_path = file_entry["file"]
        violations = file_entry["violations"]

        html_parts.append(f"<div class='file-header'><h2>File: {html.escape(file_path)}</h2>")
        html_parts.append(f"<p>Total violations: {len(violations)}</p></div>")

        if not violations:
            html_parts.append("<p>No violations ✅</p>")
            continue

        html_parts.append("<table class='violations-table'>")
        html_parts.append("<tr><th>Line</th><th>Rule ID</th><th>Severity</th><th>Message</th><th>Reference</th></tr>")
        for v in violations:
            line = v.get("line") or ""
            rule_id = html.escape(v.get("rule_id", ""))
            msg = html.escape(v.get("message", ""))
            sev = v.get("severity") or "unspecified"
            ref = html.escape(v.get("reference") or "")
            sev_class = f"severity-{sev.lower()}"
            html_parts.append(
                f"<tr>"
                f"<td>{line}</td>"
                f"<td>{rule_id}</td>"
                f"<td class='{sev_class}'>{html.escape(sev)}</td>"
                f"<td>{msg}</td>"
                f"<td>{ref}</td>"
                f"</tr>"
            )
        html_parts.append("</table>")

    html_parts.append("</body></html>")

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"[ComplyC] HTML report written to {outfile}")
