import hashlib
import html
import os
from pathlib import Path


def publish_report(result: dict) -> str:
    directory = Path(os.getenv("DQ_REPORTS_DIR", "/opt/airflow/reports"))
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(result["run_id"]).encode()).hexdigest()[:16]
    rows = "".join(
        "<tr><td>"
        + html.escape(rule["name"])
        + "</td><td>"
        + ("PASS" if rule["passed"] else "FAIL")
        + "</td><td>"
        + html.escape(rule["details"])
        + "</td></tr>"
        for rule in result["rules"]
    )
    passed = all(rule["passed"] for rule in result["rules"])
    content = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Data Quality</title>'
        "<style>body{font:16px Arial;margin:32px}table{border-collapse:collapse}"
        "td,th{border:1px solid #bbb;padding:10px;text-align:left}</style></head><body>"
        "<h1>Data Quality: "
        + ("PASS" if passed else "FAIL")
        + "</h1><p>"
        + html.escape(result["checked_at"])
        + "</p><p>Run: "
        + html.escape(str(result["run_id"]))
        + "</p><table><tr><th>Rule</th>"
        "<th>Result</th><th>Details</th></tr>" + rows + "</table></body></html>"
    )
    report = directory / f"dq_{key}.html"
    for path in (report, directory / "latest.html"):
        temporary = path.with_suffix(".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    if not passed:
        failed = [rule["name"] for rule in result["rules"] if not rule["passed"]]
        raise ValueError(f"Data Quality: {failed}. Report: {report}")
    return str(report)