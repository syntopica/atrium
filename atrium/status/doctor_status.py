"""The document the refresh job publishes after its doctor run."""

from typing import Any

from atrium.doctor.finding import Finding
from atrium.status.doctor_report import doctor_report
from atrium.status.iso_utc import iso_utc


def doctor_status(findings: list[Finding], now: float) -> dict[str, Any]:
    """Return the doctor report stamped with the instant it was written."""
    return {**doctor_report(findings), "writtenAt": iso_utc(now)}
