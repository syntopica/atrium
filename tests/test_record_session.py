"""`record-session` writes exactly one redacted record for a frozen checkpoint."""

import json
from datetime import UTC, datetime

import pytest
from session_transcript import SessionTranscript as T

from atrium.session.record_session import record_session
from atrium.session.session_state_path import session_state_path
from atrium.session.session_stop_decision import session_stop_decision
from atrium.synthesize.synthesis_registry import read_records

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _tmp_is_not_scratch(monkeypatch, tmp_path):
    """Drop the temporary root pytest itself is using from the scratch rule.

    Which root that is depends on the platform - /var/folders on macOS, /tmp on
    Linux - so a hard-coded tuple passed here and silenced every decision on CI.
    The other roots stay, which is what keeps the explicit scratch case honest.
    """
    from atrium.session.is_scratch_path import _ROOTS

    monkeypatch.setattr(
        "atrium.session.is_scratch_path._ROOTS",
        tuple(root for root in _ROOTS if not str(tmp_path).startswith(root + "/")),
    )


GOOD = {
    "title": "Cache expiry",
    "summary": "TTL checked on read.",
    "facts": ["TTL is 300s"],
    "open_ends": [],
}


def _frozen(tmp_path):
    cwd = tmp_path / "home" / "p" / "proj"
    cwd.mkdir(parents=True)
    (cwd / ".git").mkdir()
    transcript = T(tmp_path / "s1.jsonl").append(
        T.prompt("u1", "do it", "2026-09-16T11:00:00Z"),
        T.answer("a1", "done " * 8_000, "2026-09-16T11:05:00Z"),
    )
    environ = {"ATRIUM_STATE": str(tmp_path / "state")}
    payload = {"session_id": "s1", "transcript_path": str(transcript.path), "cwd": str(cwd)}
    assert session_stop_decision(payload, environ, NOW) is not None
    checkpoint = json.loads(session_state_path("s1", environ).read_text())["pending"]["id"]
    return transcript, environ, checkpoint, tmp_path / "registry"


def test_writes_the_record_at_the_frozen_boundary_even_after_the_transcript_grew(tmp_path):
    transcript, environ, checkpoint, registry = _frozen(tmp_path)
    transcript.append(
        T.tool_result("t1", "2026-09-16T11:06:00Z"),
        T.answer("a2", "recorded", "2026-09-16T11:06:05Z"),
    )
    outcome = record_session(checkpoint, json.dumps(GOOD), registry, environ)
    assert outcome.status == 0, outcome.stderr
    receipt = json.loads(outcome.stdout)
    assert receipt["recorded"] == "new"
    records = list(read_records(registry))
    assert len(records) == 1
    record = records[0]
    assert record["session"]["boundary_uuid"] == "a1"
    assert record["segmentation"] == "session-self-v1"
    assert record["model_requested"] == "session-claude-fable-5-1"
    assert record["workspace"].endswith("/p/proj")
    assert record["authored_at"] == "2026-09-16T11:05:00.000Z"
    assert record["event_ids"] == []
    state = json.loads(session_state_path("s1", environ).read_text())
    assert state["pending"] is None and state["consumed"]["job_key"] == record["job_key"]


def test_second_call_is_a_no_op_and_a_consumed_checkpoint_is_gone(tmp_path):
    _, environ, checkpoint, registry = _frozen(tmp_path)
    assert record_session(checkpoint, json.dumps(GOOD), registry, environ).status == 0
    again = record_session(checkpoint, json.dumps(GOOD), registry, environ)
    assert again.status == 3 and "no pending checkpoint" in again.stderr
    assert len(list(read_records(registry))) == 1


def test_nothing_durable_consumes_without_a_record(tmp_path):
    _, environ, checkpoint, registry = _frozen(tmp_path)
    outcome = record_session(checkpoint, "", registry, environ, nothing_durable=True)
    assert outcome.status == 0 and "nothing durable" in outcome.stdout
    assert list(read_records(registry)) == []
    assert json.loads(session_state_path("s1", environ).read_text())["consumed"]["job_key"] is None


def test_invalid_payloads_are_refused_with_a_reason_and_keep_the_checkpoint(tmp_path):
    _, environ, checkpoint, registry = _frozen(tmp_path)
    cases = [
        ({**GOOD, "extra": 1}, "unknown keys: extra"),
        ({k: v for k, v in GOOD.items() if k != "open_ends"}, "open_ends must be a list"),
        ({**GOOD, "facts": [1]}, "facts must be a list of strings"),
        ({**GOOD, "title": "  "}, "title must be a non-empty string"),
    ]
    for payload, reason in cases:
        outcome = record_session(checkpoint, json.dumps(payload), registry, environ)
        assert outcome.status == 2 and reason in outcome.stderr
    assert record_session(checkpoint, "not json", registry, environ).status == 2
    assert record_session(checkpoint, json.dumps(GOOD), registry, environ).status == 0


def test_secrets_in_the_synthesis_are_redacted_before_the_write(tmp_path):
    _, environ, checkpoint, registry = _frozen(tmp_path)
    payload = {
        **GOOD,
        "facts": ["password: hunter2hunter2", "token Bearer abcdefghijklmnopqrstuvwxyz"],
    }
    outcome = record_session(checkpoint, json.dumps(payload), registry, environ)
    assert outcome.status == 0
    record = next(iter(read_records(registry)))
    assert record["output"]["facts"] == [
        "password: [REDACTED:secret]",
        "token Bearer [REDACTED:token]",
    ]
    assert "hunter2hunter2" not in outcome.stdout


def test_disabled_environment_and_unknown_ids_are_refused(tmp_path):
    _, environ, checkpoint, registry = _frozen(tmp_path)
    off = record_session(
        checkpoint, json.dumps(GOOD), registry, {**environ, "ATRIUM_NO_SESSION_RECORD": "1"}
    )
    assert off.status == 3
    assert record_session("../../etc", json.dumps(GOOD), registry, environ).status == 3
    assert record_session("0" * 16, json.dumps(GOOD), registry, environ).status == 3
