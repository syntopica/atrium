"""When a stopping session owes a record, and when the hook stays silent."""

import json
from datetime import UTC, datetime

import pytest
from session_transcript import SessionTranscript as T

from atrium.session.session_state_path import session_state_path
from atrium.session.session_stop_decision import session_stop_decision

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


def _session(tmp_path, entrypoint="cli"):
    """A project cwd, a transcript, and the environment pointing at a fresh state dir."""
    cwd = tmp_path / "home" / "p" / "proj"
    cwd.mkdir(parents=True)
    (cwd / ".git").mkdir()
    transcript = tmp_path / "transcripts" / "s1.jsonl"
    transcript.parent.mkdir()
    environ = {"ATRIUM_STATE": str(tmp_path / "state")}
    return cwd, T(transcript, entrypoint), environ


def _payload(cwd, transcript, **extra):
    return {
        "session_id": "s1",
        "transcript_path": str(transcript.path),
        "cwd": str(cwd),
        "stop_hook_active": False,
        **extra,
    }


def _big_session(transcript):
    """Enough transcript to cross the byte limit, with a prompt and an answer."""
    transcript.append(
        T.prompt("u1", "please do the thing", "2026-09-16T11:00:00Z"),
        T.answer("a1", "done " * 8_000, "2026-09-16T11:05:00Z"),
    )


def test_refuses_above_the_byte_limit_and_freezes_the_boundary(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    _big_session(transcript)
    decision = session_stop_decision(_payload(cwd, transcript), environ, NOW)
    assert decision is not None and decision["decision"] == "block"
    state = json.loads(session_state_path("s1", environ).read_text())
    pending = state["pending"]
    assert pending["boundary_uuid"] == "a1"
    assert pending["since"] == "2026-09-16T11:00:00.000Z"
    assert pending["model"] == "claude-fable-5-1"
    assert f"--checkpoint {pending['id']}" in decision["reason"]
    assert decision["systemMessage"].startswith("atrium: recording")
    assert pending["id"] in decision["systemMessage"]
    assert decision["suppressOutput"] is True
    assert state["workspace"].endswith("/p/proj")


def test_silent_under_the_limits_and_without_a_prompt(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    transcript.append(
        T.prompt("u1", "hi", "2026-09-16T11:59:00Z"),
        T.answer("a1", "hello", "2026-09-16T11:59:01Z"),
    )
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is None
    # Aged but tiny: still silent; aged and over the small limit: refused.
    transcript.append(T.answer("a2", "x" * 5_000, "2026-09-16T11:59:02Z"))
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is None
    # Past the hour the age rule waits: the limits count prompts, and a
    # single-prompt interval is recorded only once it has aged.
    later = datetime(2026, 9, 16, 13, 5, tzinfo=UTC)
    assert session_stop_decision(_payload(cwd, transcript), environ, later) is not None


def test_attachments_and_snapshots_do_not_count_as_new_work(tmp_path):
    """A re-read of the instruction files after compaction is not an episode."""
    cwd, transcript, environ = _session(tmp_path)
    transcript.append(
        T.prompt("u1", "status?", "2026-09-16T11:59:00Z"),
        T.attachment("2026-09-16T11:59:01Z", size=100_000),
        T.answer("a1", "fine", "2026-09-16T11:59:02Z"),
    )
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is None


def test_silent_for_scratch_sdk_subagent_and_opted_out_sessions(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    _big_session(transcript)
    payload = _payload(cwd, transcript)
    assert session_stop_decision(payload, {**environ, "ATRIUM_NO_SESSION_RECORD": "1"}, NOW) is None
    assert session_stop_decision({**payload, "agent_id": "x"}, environ, NOW) is None
    assert (
        session_stop_decision({**payload, "cwd": "/var/folders/claude-1/x"}, environ, NOW) is None
    )
    scratch = tmp_path / "-private-tmp-x" / "t.jsonl"
    scratch.parent.mkdir()
    scratch.write_bytes(transcript.path.read_bytes())
    assert session_stop_decision({**payload, "transcript_path": str(scratch)}, environ, NOW) is None
    _, sdk, _ = _session(tmp_path / "sdk", entrypoint="sdk-py")
    _big_session(sdk)
    assert session_stop_decision(_payload(cwd, sdk), environ, NOW) is None


def test_ignored_refusal_is_repeated_twice_then_left_pending(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    _big_session(transcript)
    first = session_stop_decision(_payload(cwd, transcript), environ, NOW)
    assert first is not None
    active = _payload(cwd, transcript, stop_hook_active=True)
    assert session_stop_decision(active, environ, NOW) is not None
    assert session_stop_decision(active, environ, NOW) is not None
    assert session_stop_decision(active, environ, NOW) is None
    state = json.loads(session_state_path("s1", environ).read_text())
    assert state["pending"]["attempts"] == 3
    # The next ordinary turn re-issues it with the same id.
    again = session_stop_decision(_payload(cwd, transcript), environ, NOW)
    assert again is not None and state["pending"]["id"] in again["reason"]


def test_consumed_checkpoint_silences_the_active_turn(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    _big_session(transcript)
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is not None
    path = session_state_path("s1", environ)
    state = json.loads(path.read_text())
    state["consumed"] = {
        "offset": transcript.path.stat().st_size,
        "at": "2026-09-16T11:05:00.000Z",
        "job_key": "k",
    }
    state["pending"] = None
    path.write_text(json.dumps(state))
    assert (
        session_stop_decision(_payload(cwd, transcript, stop_hook_active=True), environ, NOW)
        is None
    )
    # Bookkeeping after the boundary (a tool result) is not new work.
    transcript.append(
        T.tool_result("t1", "2026-09-16T11:06:00Z"), T.attachment("2026-09-16T11:06:01Z")
    )
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is None


def test_checkpoint_whose_boundary_vanished_is_dropped(tmp_path):
    cwd, transcript, environ = _session(tmp_path)
    _big_session(transcript)
    assert session_stop_decision(_payload(cwd, transcript), environ, NOW) is not None
    transcript.path.write_text("")
    T(transcript.path).append(T.prompt("u9", "fresh start", "2026-09-16T11:50:00Z"))
    assert (
        session_stop_decision(_payload(cwd, transcript, stop_hook_active=True), environ, NOW)
        is None
    )
    assert json.loads(session_state_path("s1", environ).read_text())["pending"] is None
