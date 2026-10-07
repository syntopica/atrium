"""The `doctor` handler of the atrium CLI."""

from pathlib import Path

from atrium.state.state_directory import state_directory
from atrium.synthesize.default_registry import default_registry


def run_doctor(
    index: Path, archive: Path, stamp: Path, *, as_json: bool = False, publish: bool = False
) -> int:
    """Report every coherence check, and fail when the memory is answering wrongly.

    Everything this looks at had already gone wrong silently: a sync eleven days
    dead behind a stale lock, a manifest outranking the records under it, a
    refresh that reports "done" whatever happened. None of those were subtle --
    they were invisible because nothing printed the right number.
    """
    from atrium.doctor.run_doctor import run_doctor

    findings = run_doctor(index, archive, stamp, default_registry())
    if publish:
        import time

        from atrium.status.doctor_status import doctor_status
        from atrium.status.publish_json_atomically import publish_json_atomically
        from atrium.status.status_file import status_file

        publish_json_atomically(
            status_file(state_directory(), "doctor"), doctor_status(findings, time.time())
        )
    if as_json:
        import json

        from atrium.status.doctor_report import doctor_report

        report = doctor_report(findings)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["ok"] else 1
    mark = {"ok": "ok  ", "warn": "warn", "broken": "FAIL"}
    for finding in findings:
        print(f"  {mark[finding.severity]} {finding.check:<16} {finding.summary}")
    broken = [finding for finding in findings if finding.severity == "broken"]
    if broken:
        print(f"  {len(broken)} check(s) say this index answers from a world that moved on")
        return 1
    return 0
