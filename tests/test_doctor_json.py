"""`doctor --json` publishes fixed codes, never the prose or numbers behind them."""

import json

import pytest

from atrium.cli import main
from atrium.doctor.finding import CODE_PATTERN, Finding
from atrium.doctor.refresh_health import refresh_health
from atrium.status.doctor_report import doctor_report


def _finding(severity, code):
    return Finding(
        check="refresh",
        severity=severity,
        summary="host-1: /private/path and a conversation id",
        detail={"path": "/private/path"},
        code=code,
    )


def test_a_finding_rejects_prose_as_its_code():
    with pytest.raises(ValueError, match="fixed machine word"):
        _finding("ok", "last refresh finished 10s ago")


def test_the_report_carries_name_ok_severity_and_code_only():
    report = doctor_report([_finding("ok", "refresh_fresh"), _finding("warn", "refresh_stale")])
    assert report == {
        "schemaVersion": 1,
        "ok": True,
        "checks": [
            {"name": "refresh", "ok": True, "severity": "ok", "code": "refresh_fresh"},
            {"name": "refresh", "ok": False, "severity": "warn", "code": "refresh_stale"},
        ],
    }


def test_a_broken_check_fails_the_report():
    assert doctor_report([_finding("broken", "refresh_dead")])["ok"] is False


def test_refresh_codes_follow_the_severity(tmp_path):
    stamp = tmp_path / "last-refresh"
    assert refresh_health(stamp).code == "refresh_never_recorded"
    stamp.write_text("1000")
    assert refresh_health(stamp, now=1060).code == "refresh_fresh"
    assert refresh_health(stamp, now=1000 + 7200).code == "refresh_stale"
    assert refresh_health(stamp, now=1000 + 86400).code == "refresh_dead"


def test_the_command_prints_json_with_codes_and_a_matching_exit(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ATRIUM_STATE", str(tmp_path / "state"))
    code = main(
        [
            "--index",
            str(tmp_path / "index.sqlite3"),
            "doctor",
            "--json",
            "--archive",
            str(tmp_path / "absent.jsonl"),
        ]
    )
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["schemaVersion"] == 1
    assert code == (0 if report["ok"] else 1)
    # No archive and no stamp: both are broken, and say so by code.
    by_name = {check["name"]: check for check in report["checks"]}
    assert by_name["archive"]["code"] == "archive_missing"
    assert by_name["refresh"]["code"] == "refresh_never_recorded"
    assert report["ok"] is False
    for check in report["checks"]:
        assert set(check) == {"name", "ok", "severity", "code"}
        assert CODE_PATTERN.fullmatch(check["code"])
    assert str(tmp_path) not in out
