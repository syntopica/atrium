"""The machine-readable form of a doctor run."""

from typing import Any

from atrium.doctor.finding import Finding
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION


def doctor_report(findings: list[Finding]) -> dict[str, Any]:
    """Return each check's name, verdict and fixed code -- never its summary or detail.

    Summaries and details carry host names, paths and conversation ids; the
    code is the whole machine answer. ``ok`` is true only for a healthy check,
    so a drifting one reads false with ``severity`` ``warn``; the top-level
    ``ok`` mirrors the exit status, which fails only on ``broken``.
    """
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "ok": all(finding.severity != "broken" for finding in findings),
        "checks": [
            {
                "name": finding.check,
                "ok": finding.severity == "ok",
                "severity": finding.severity,
                "code": finding.code,
            }
            for finding in findings
        ],
    }
