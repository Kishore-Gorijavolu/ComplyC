"""
reporters.py – JSON and HTML report generators for ComplyC
"""

from __future__ import annotations

import json
import html
from dataclasses import asdict
from typing import Dict, List

from collections import Counter

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
.dashboard {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 22px;
}

.dashboard-card {
  flex: 1;
  min-width: 150px;
  border: 1px solid #ccc;
  border-left: 5px solid #4a78c2;
  background: #f8fbff;
  padding: 14px;
  border-radius: 6px;
}

.dashboard-value {
  font-size: 28px;
  font-weight: bold;
  color: #222;
}

.dashboard-label {
  font-size: 13px;
  color: #555;
  margin-top: 4px;
}
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
    
    s = data["summary"]
    
    # Dashboard section
    critical_count = s["by_severity"].get("critical", 0)
    major_count = s["by_severity"].get("major", 0)
    minor_count = s["by_severity"].get("minor", 0)
    unspecified_count = s["by_severity"].get("unspecified", 0)

    html_parts.append("<h2>Dashboard</h2>")
    html_parts.append("<div class='dashboard'>")

    cards = [
        ("Files Scanned", s["total_files"]),
        ("Total Violations", s["total_violations"]),
        ("Critical", critical_count),
        ("Major", major_count),
        ("Minor", minor_count),
        ("Unspecified", unspecified_count),
    ]

    for label, value in cards:
        html_parts.append(
            "<div class='dashboard-card'>"
            f"<div class='dashboard-value'>{value}</div>"
            f"<div class='dashboard-label'>{html.escape(label)}</div>"
            "</div>"
        )

    html_parts.append("</div>")

    # Summary section
    #s = data["summary"]
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

    # Rule summary section
    rule_summary = {}

    for file_entry in data["files"]:
        for violation in file_entry["violations"]:
            rule_id = violation.get("rule_id") or "UNSPECIFIED_RULE"
            severity = (violation.get("severity") or "unspecified").lower()

            if rule_id not in rule_summary:
                rule_summary[rule_id] = {
                    "total": 0,
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "unspecified": 0,
                }

            rule_summary[rule_id]["total"] += 1
            rule_summary[rule_id][severity] = rule_summary[rule_id].get(severity, 0) + 1

    html_parts.append("<h2>Rule Summary</h2>")

    if rule_summary:
        html_parts.append("<table class='summary-table'>")
        html_parts.append(
            "<tr>"
            "<th>Rule ID</th>"
            "<th>Total</th>"
            "<th>Critical</th>"
            "<th>Major</th>"
            "<th>Minor</th>"
            "<th>Unspecified</th>"
            "</tr>"
        )

        total_counts = {
            "total": 0,
            "critical": 0,
            "major": 0,
            "minor": 0,
            "unspecified": 0,
        }

        for rule_id, counts in sorted(
            rule_summary.items(),
            key=lambda item: item[1]["total"],
            reverse=True,
        ):
            total_counts["total"] += counts.get("total", 0)
            total_counts["critical"] += counts.get("critical", 0)
            total_counts["major"] += counts.get("major", 0)
            total_counts["minor"] += counts.get("minor", 0)
            total_counts["unspecified"] += counts.get("unspecified", 0)

            html_parts.append(
                "<tr>"
                f"<td>{html.escape(rule_id)}</td>"
                f"<td>{counts.get('total', 0)}</td>"
                f"<td>{counts.get('critical', 0)}</td>"
                f"<td>{counts.get('major', 0)}</td>"
                f"<td>{counts.get('minor', 0)}</td>"
                f"<td>{counts.get('unspecified', 0)}</td>"
                "</tr>"
            )

        html_parts.append(
            "<tr style='font-weight:bold; background:#f5f5f5;'>"
            "<td>TOTAL</td>"
            f"<td>{total_counts['total']}</td>"
            f"<td>{total_counts['critical']}</td>"
            f"<td>{total_counts['major']}</td>"
            f"<td>{total_counts['minor']}</td>"
            f"<td>{total_counts['unspecified']}</td>"
            "</tr>"
        )

        html_parts.append("</table>")
    else:
        html_parts.append("<p>No rule violations found.</p>")

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
