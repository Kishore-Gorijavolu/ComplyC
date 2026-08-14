"""
reporters.py – JSON and HTML report generators for ComplyC
"""

from __future__ import annotations

import csv
import json
import html
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from collections import Counter

from .rule_engine import CHECK_HANDLERS, SUPPORTED_SCOPES, Violation


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



def write_csv_report(per_file: Dict[str, List[Violation]], outfile: str):
    """Write a flat CSV report suitable for Excel and issue tracking imports."""
    fieldnames = [
        "file",
        "line",
        "rule_id",
        "severity",
        "message",
        "reference",
    ]

    with open(outfile, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for file_path, violations in per_file.items():
            for violation in violations:
                writer.writerow({
                    "file": file_path,
                    "line": violation.line if violation.line is not None else "",
                    "rule_id": violation.rule_id,
                    "severity": violation.severity or "unspecified",
                    "message": violation.message,
                    "reference": violation.reference or "",
                })

    print(f"[ComplyC] CSV report written to {outfile}")

def write_html_report(
    per_file: Dict[str, List[Violation]],
    outfile: str,
    rules: Optional[List[Dict[str, Any]]] = None,
):
    """Write a simple but clean HTML report."""
    data = violations_to_dict(per_file)

    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html><head><meta charset='UTF-8'>")
    html_parts.append("<title>ComplyC Report</title>")
    html_parts.append("""
<style>
body {
  font-family: Arial, sans-serif;
  margin: 20px;
  color: #222;
}

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

/* ===== Two half-page summary panels ===== */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin: 10px 0 24px 0;
}

.overview-card {
  border: 1px solid #ccc;
  border-radius: 6px;
  background: #fafafa;
  padding: 16px;
  min-width: 0;
}

.overview-title {
  margin: 0 0 14px 0;
  font-size: 22px;
}

.overview-subtitle {
  font-size: 13px;
  color: #777;
  font-weight: normal;
}

.chart-layout {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.pie-wrap {
  position: relative;
  width: 210px;
  height: 210px;
  flex: 0 0 210px;
}

.pie-chart {
  width: 210px;
  height: 210px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06);
}

.pie-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: bold;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.35);
  pointer-events: none;
}

.chart-details {
  flex: 1;
  min-width: 235px;
}

.chart-legend {
  list-style: none;
  padding: 0;
  margin: 0;
}

.chart-legend li {
  display: grid;
  grid-template-columns: 16px 1fr auto;
  align-items: center;
  gap: 8px;
  margin: 9px 0;
}

.legend-dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  display: inline-block;
}

.legend-value {
  font-weight: bold;
  white-space: nowrap;
}

.chart-separator {
  border: 0;
  border-top: 1px solid #ccc;
  margin: 14px 0;
}

.chart-note {
  color: #555;
  font-size: 13px;
  line-height: 1.45;
  margin: 10px 0 0 0;
}

.compliance-good {
  color: #20813a;
  font-weight: bold;
}

/* ===== Tables ===== */
.summary-table,
.violations-table {
  border-collapse: collapse;
  margin-bottom: 20px;
  width: 100%;
}

.summary-table th,
.summary-table td,
.violations-table th,
.violations-table td {
  border: 1px solid #ccc;
  padding: 6px 8px;
  font-size: 14px;
}

.summary-table th,
.violations-table th {
  background: #f2f2f2;
}

.rule-id {
  color: #0645ad;
}

.status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: bold;
  white-space: nowrap;
}

.status-findings {
  background: #fff0e6;
  color: #9a4d00;
  border: 1px solid #f2c08f;
}

.status-compliant {
  background: #eaf7ed;
  color: #1f6f35;
  border: 1px solid #a9d7b4;
}

.status-not-evaluated {
  background: #f1f1f1;
  color: #555;
  border: 1px solid #cfcfcf;
}

.percent-cell {
  min-width: 210px;
}

.percent-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.percent-track {
  flex: 1;
  min-width: 100px;
  height: 10px;
  background: #ececec;
  border-radius: 5px;
  overflow: hidden;
}

.percent-fill {
  height: 100%;
  border-radius: 5px;
}

.percent-value {
  width: 52px;
  text-align: right;
  white-space: nowrap;
}

.severity-critical { color: #b30000; font-weight: bold; }
.severity-major { color: #cc6600; font-weight: bold; }
.severity-minor { color: #666600; }
.severity-unspecified { color: #555; }

.file-header {
  background: #e9f0fb;
  padding: 8px;
  margin-top: 20px;
  border-left: 4px solid #4a78c2;
}

@media (max-width: 950px) {
  .overview-grid { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  body { margin: 12px; }
  .chart-layout { justify-content: center; }
  .chart-details { min-width: 100%; }
}
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

    # -----------------------------------------------------------------
    # Summary chart data
    # -----------------------------------------------------------------

    # Limited security-oriented rules currently implemented in this beta.
    #
    # Compliance is calculated using FILE x RULE opportunities:
    #
    #   opportunities = scanned_files * limited_security_rule_count
    #
    # A file/rule opportunity is marked non-compliant when at least one
    # violation of that rule is reported for that file. Multiple findings
    # of the same rule in the same file still represent one failed check.
    #
    # This keeps the percentage bounded from 0% to 100% and avoids treating
    # raw violation count as a compliance percentage.
    limited_security_rules = {
        "SAFETY_FORBIDDEN_API_001": "Unsafe / Restricted C APIs",
        "SAFETY_DYNAMIC_MEM_001": "Dynamic Memory",
        "SAFETY_RECURSION_001": "Recursion",
    }

    failed_security_pairs = set()
    security_finding_count = 0

    for file_entry in data["files"]:
        file_path = file_entry["file"]

        for violation in file_entry["violations"]:
            rule_id = violation.get("rule_id") or ""

            if rule_id in limited_security_rules:
                failed_security_pairs.add((file_path, rule_id))
                security_finding_count += 1

    security_rule_count = len(limited_security_rules)
    security_opportunities = s["total_files"] * security_rule_count
    failed_security_checks = len(failed_security_pairs)
    compliant_security_checks = max(
        security_opportunities - failed_security_checks, 0
    )

    if security_opportunities > 0:
        security_noncompliant_pct = (
            failed_security_checks / security_opportunities
        ) * 100.0
        security_compliant_pct = 100.0 - security_noncompliant_pct
    else:
        # With no files there is nothing meaningful to score.
        security_compliant_pct = 100.0
        security_noncompliant_pct = 0.0

    security_compliant_pct = max(0.0, min(100.0, security_compliant_pct))
    security_noncompliant_pct = max(
        0.0, min(100.0, security_noncompliant_pct)
    )

    # Build complete rule summary once. The table is seeded from the
    # configured YAML rules, not only from returned violations. This means
    # zero-finding rules remain visible and reviewers can distinguish:
    #
    #   - Evaluated / Findings
    #   - Evaluated / Compliant
    #   - Configured / Not Evaluated
    #
    # A rule is considered executable when its scope is supported and its
    # handler is registered in CHECK_HANDLERS.
    configured_rules = rules or []
    rule_summary = {}

    for configured_rule in configured_rules:
        rule_id = configured_rule.get("id") or "UNSPECIFIED_RULE"
        scope = configured_rule.get("scope", "file")
        check_name = configured_rule.get("check")

        executable = (
            scope in SUPPORTED_SCOPES
            and bool(check_name)
            and check_name in CHECK_HANDLERS
        )

        if not executable:
            reasons = []
            if scope not in SUPPORTED_SCOPES:
                reasons.append(f"unsupported scope: {scope}")
            if not check_name:
                reasons.append("missing check handler")
            elif check_name not in CHECK_HANDLERS:
                reasons.append(f"unknown handler: {check_name}")
            evaluation_note = "; ".join(reasons) or "not evaluated"
        else:
            evaluation_note = ""

        rule_summary[rule_id] = {
            "title": configured_rule.get("title") or "",
            "scope": scope,
            "handler": check_name or "",
            "evaluated": executable,
            "evaluation_note": evaluation_note,
            "total": 0,
            "critical": 0,
            "major": 0,
            "minor": 0,
            "unspecified": 0,
        }

    # Count actual violations. If write_html_report() is called without rule
    # metadata, retain backward-compatible behavior by adding encountered rules.
    for file_entry in data["files"]:
        for violation in file_entry["violations"]:
            rule_id = violation.get("rule_id") or "UNSPECIFIED_RULE"
            severity = (violation.get("severity") or "unspecified").lower()

            if rule_id not in rule_summary:
                rule_summary[rule_id] = {
                    "title": "",
                    "scope": "",
                    "handler": "",
                    "evaluated": True,
                    "evaluation_note": "",
                    "total": 0,
                    "critical": 0,
                    "major": 0,
                    "minor": 0,
                    "unspecified": 0,
                }

            rule_summary[rule_id]["total"] += 1
            rule_summary[rule_id][severity] = (
                rule_summary[rule_id].get(severity, 0) + 1
            )

    evaluated_rule_count = sum(
        1 for counts in rule_summary.values() if counts.get("evaluated")
    )
    finding_rule_count = sum(
        1
        for counts in rule_summary.values()
        if counts.get("evaluated") and counts.get("total", 0) > 0
    )
    compliant_rule_count = sum(
        1
        for counts in rule_summary.values()
        if counts.get("evaluated") and counts.get("total", 0) == 0
    )
    not_evaluated_rule_count = sum(
        1 for counts in rule_summary.values() if not counts.get("evaluated")
    )

    # -----------------------------------------------------------------
    # Security compliance pie
    # -----------------------------------------------------------------
    compliant_color = "#28a745"
    noncompliant_color = "#dc3545"

    if security_noncompliant_pct <= 0.0:
        security_gradient = f"{compliant_color} 0% 100%"
    elif security_compliant_pct <= 0.0:
        security_gradient = f"{noncompliant_color} 0% 100%"
    else:
        security_gradient = (
            f"{compliant_color} 0% {security_compliant_pct:.2f}%, "
            f"{noncompliant_color} {security_compliant_pct:.2f}% 100%"
        )

    # -----------------------------------------------------------------
    # Rule severity pie
    # -----------------------------------------------------------------
    severity_counts = {
        "Critical": critical_count,
        "Major": major_count,
        "Minor": minor_count,
        "Unspecified": unspecified_count,
    }

    severity_colors = {
        "Critical": "#e53935",
        "Major": "#fb8c00",
        "Minor": "#fbc02d",
        "Unspecified": "#9e9e9e",
    }

    severity_total = sum(severity_counts.values())
    severity_gradient_parts = []
    severity_legend_parts = []
    severity_cursor = 0.0

    for label in ("Critical", "Major", "Minor", "Unspecified"):
        count = severity_counts[label]
        pct = (count / severity_total * 100.0) if severity_total else 0.0
        color = severity_colors[label]

        if count > 0:
            start_pct = severity_cursor
            severity_cursor += pct
            severity_gradient_parts.append(
                f"{color} {start_pct:.2f}% {severity_cursor:.2f}%"
            )

        severity_legend_parts.append(
            "<li>"
            f"<span class='legend-dot' style='background:{color};'></span>"
            f"<span>{html.escape(label)}</span>"
            f"<span class='legend-value'>{pct:.1f}% ({count})</span>"
            "</li>"
        )

    severity_gradient = (
        ", ".join(severity_gradient_parts)
        if severity_gradient_parts
        else "#d9d9d9 0% 100%"
    )

    # -----------------------------------------------------------------
    # Two half-page cards
    # -----------------------------------------------------------------
    html_parts.append("<div class='overview-grid'>")

    # LEFT CARD
    html_parts.append("<section class='overview-card'>")
    html_parts.append(
        "<h2 class='overview-title'>"
        "Security-Oriented Findings "
        "<span class='overview-subtitle'>(Limited Beta Checks)</span>"
        "</h2>"
    )
    html_parts.append("<div class='chart-layout'>")
    html_parts.append("<div class='pie-wrap'>")
    html_parts.append(
        f"<div class='pie-chart' "
        f"style='background:conic-gradient({security_gradient});'></div>"
    )
    html_parts.append(
        f"<div class='pie-center'>{security_compliant_pct:.1f}%</div>"
    )
    html_parts.append("</div>")

    html_parts.append("<div class='chart-details'>")
    html_parts.append("<ul class='chart-legend'>")
    html_parts.append(
        "<li>"
        f"<span class='legend-dot' style='background:{compliant_color};'></span>"
        "<span>Compliant</span>"
        f"<span class='legend-value'>{security_compliant_pct:.1f}% "
        f"({compliant_security_checks})</span>"
        "</li>"
    )
    html_parts.append(
        "<li>"
        f"<span class='legend-dot' style='background:{noncompliant_color};'></span>"
        "<span>Not Compliant</span>"
        f"<span class='legend-value'>{security_noncompliant_pct:.1f}% "
        f"({failed_security_checks})</span>"
        "</li>"
    )
    html_parts.append("</ul>")
    html_parts.append("<hr class='chart-separator'>")

    if failed_security_checks == 0:
        html_parts.append(
            "<p class='chart-note compliance-good'>"
            "Excellent! No violations were detected by the limited "
            "security-oriented checks enabled in this scan."
            "</p>"
        )
    else:
        html_parts.append(
            "<p class='chart-note'>"
            f"{failed_security_checks} of {security_opportunities} "
            "limited security file/rule checks were non-compliant. "
            f"{security_finding_count} security-oriented violation(s) "
            "were reported."
            "</p>"
        )

    html_parts.append(
        "<p class='chart-note'>"
        "This percentage applies only to the limited security-oriented "
        "checks currently implemented in ComplyC Beta. It does not mean "
        "the analyzed software is free of cybersecurity vulnerabilities."
        "</p>"
    )
    html_parts.append("</div></div></section>")

    # RIGHT CARD
    html_parts.append("<section class='overview-card'>")
    html_parts.append(
        "<h2 class='overview-title'>Rule Summary Findings</h2>"
    )
    html_parts.append("<div class='chart-layout'>")
    html_parts.append("<div class='pie-wrap'>")
    html_parts.append(
        f"<div class='pie-chart' "
        f"style='background:conic-gradient({severity_gradient});'></div>"
    )
    html_parts.append(
        f"<div class='pie-center'>{severity_total}</div>"
    )
    html_parts.append("</div>")
    html_parts.append("<div class='chart-details'>")
    html_parts.append("<ul class='chart-legend'>")
    html_parts.extend(severity_legend_parts)
    html_parts.append("</ul>")
    html_parts.append("<hr class='chart-separator'>")
    html_parts.append(
        f"<p class='chart-note'><strong>Total Violations: "
        f"{severity_total}</strong></p>"
    )
    html_parts.append(
        "<p class='chart-note'>"
        f"<strong>{evaluated_rule_count}</strong> rules evaluated: "
        f"<strong>{finding_rule_count}</strong> with findings and "
        f"<strong>{compliant_rule_count}</strong> with zero findings."
        "</p>"
    )
    if not_evaluated_rule_count:
        html_parts.append(
            "<p class='chart-note'>"
            f"<strong>{not_evaluated_rule_count}</strong> configured rule(s) "
            "were not evaluated and are identified in the detailed table below."
            "</p>"
        )
    html_parts.append("</div></div></section>")
    html_parts.append("</div>")

    # -----------------------------------------------------------------
    # Detailed Rule Summary
    # -----------------------------------------------------------------
    html_parts.append("<h2>Rule Summary (Details)</h2>")

    if rule_summary:
        html_parts.append("<table class='summary-table'>")
        html_parts.append(
            "<tr>"
            "<th>Rule ID</th>"
            "<th>Status</th>"
            "<th>Total</th>"
            "<th>Critical</th>"
            "<th>Major</th>"
            "<th>Minor</th>"
            "<th>Unspecified</th>"
            "<th>% of Total</th>"
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

            rule_pct = (
                counts.get("total", 0) / s["total_violations"] * 100.0
                if s["total_violations"]
                else 0.0
            )

            # Bar color reflects the highest severity present for the rule.
            if counts.get("critical", 0):
                bar_color = "#e53935"
            elif counts.get("major", 0):
                bar_color = "#fb8c00"
            elif counts.get("minor", 0):
                bar_color = "#fbc02d"
            else:
                bar_color = "#9e9e9e"

            if not counts.get("evaluated"):
                status_html = (
                    "<span class='status-badge status-not-evaluated'>"
                    "NOT EVALUATED</span>"
                )
                status_title = counts.get("evaluation_note") or "Not evaluated"
            elif counts.get("total", 0) > 0:
                status_html = (
                    "<span class='status-badge status-findings'>"
                    "FINDINGS</span>"
                )
                status_title = "Rule evaluated and one or more findings were reported."
            else:
                status_html = (
                    "<span class='status-badge status-compliant'>"
                    "COMPLIANT</span>"
                )
                status_title = "Rule evaluated with zero findings."

            html_parts.append(
                "<tr>"
                f"<td class='rule-id' title='{html.escape(counts.get('title') or '')}'>"
                f"{html.escape(rule_id)}</td>"
                f"<td title='{html.escape(status_title)}'>{status_html}</td>"
                f"<td>{counts.get('total', 0)}</td>"
                f"<td>{counts.get('critical', 0)}</td>"
                f"<td>{counts.get('major', 0)}</td>"
                f"<td>{counts.get('minor', 0)}</td>"
                f"<td>{counts.get('unspecified', 0)}</td>"
                "<td class='percent-cell'>"
                "<div class='percent-row'>"
                "<div class='percent-track'>"
                f"<div class='percent-fill' "
                f"style='width:{rule_pct:.2f}%; background:{bar_color};'></div>"
                "</div>"
                f"<span class='percent-value'>{rule_pct:.1f}%</span>"
                "</div>"
                "</td>"
                "</tr>"
            )

        html_parts.append(
            "<tr style='font-weight:bold; background:#f5f5f5;'>"
            "<td>TOTAL</td>"
            f"<td>{evaluated_rule_count} evaluated</td>"
            f"<td>{total_counts['total']}</td>"
            f"<td>{total_counts['critical']}</td>"
            f"<td>{total_counts['major']}</td>"
            f"<td>{total_counts['minor']}</td>"
            f"<td>{total_counts['unspecified']}</td>"
            "<td class='percent-cell'>"
            "<div class='percent-row'>"
            "<div class='percent-track'>"
            "<div class='percent-fill' "
            "style='width:100%; background:#2f67c7;'></div>"
            "</div>"
            "<span class='percent-value'>100%</span>"
            "</div>"
            "</td>"
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
