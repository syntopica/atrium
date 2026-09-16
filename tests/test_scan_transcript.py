"""The transcript scan reads metadata at the cost of the delta, never text."""

from session_transcript import SessionTranscript as T

from atrium.session.scan_transcript import scan_transcript


def test_boundary_is_the_last_user_or_assistant_record(tmp_path):
    path = tmp_path / "t.jsonl"
    T(path).append(
        T.prompt("u1", "hello", "2026-09-16T10:00:00.000Z"),
        T.answer("a1", "hi", "2026-09-16T10:00:05.000Z"),
        T.attachment("2026-09-16T10:00:06.000Z"),
    )
    scan = scan_transcript(path)
    assert scan.entrypoint == "cli"
    assert scan.first_at == "2026-09-16T10:00:00.000Z"
    assert scan.boundary is not None
    assert scan.boundary.uuid == "a1"
    assert scan.model == "claude-fable-5-1"
    assert scan.prompts_after == 1
    assert scan.boundary.offset < scan.size


def test_prompts_are_counted_from_the_offset_and_tool_results_do_not_count(tmp_path):
    path = tmp_path / "t.jsonl"
    transcript = T(path).append(T.prompt("u1", "first", "2026-09-16T10:00:00Z"))
    offset = path.stat().st_size
    transcript.append(
        T.tool_result("t1", "2026-09-16T10:01:00Z"), T.answer("a2", "done", "2026-09-16T10:01:05Z")
    )
    assert scan_transcript(path, offset).prompts_after == 0
    transcript.append(T.prompt("u2", "second", "2026-09-16T10:02:00Z"))
    scan = scan_transcript(path, offset)
    assert scan.prompts_after == 1
    assert scan.boundary is not None and scan.boundary.uuid == "u2"


def test_no_new_record_after_the_offset_falls_back_to_the_whole_file(tmp_path):
    path = tmp_path / "t.jsonl"
    transcript = T(path).append(T.prompt("u1", "first", "2026-09-16T10:00:00Z"))
    offset = path.stat().st_size
    transcript.append(T.attachment("2026-09-16T10:00:01Z"))
    scan = scan_transcript(path, offset)
    assert scan.boundary is not None and scan.boundary.uuid == "u1"
    assert scan.prompts_after == 0


def test_sdk_entrypoint_is_reported(tmp_path):
    path = tmp_path / "t.jsonl"
    T(path, entrypoint="sdk-py").append(T.prompt("u1", "x", "2026-09-16T10:00:00Z"))
    assert scan_transcript(path).entrypoint == "sdk-py"


def test_a_long_record_whose_type_comes_after_the_message_is_still_the_boundary(tmp_path):
    """Claude Code writes `type` after `message`; a prefix check missed 10.9 MB of a real session."""
    path = tmp_path / "t.jsonl"
    T(path).append(T.prompt("u1", "start", "2026-09-16T10:00:00Z"))
    long = {
        "parentUuid": "u1",
        "message": {"role": "assistant", "model": "claude-fable-5-1", "content": "z" * 20_000},
        "type": "assistant",
        "uuid": "a-long",
        "timestamp": "2026-09-16T10:09:00Z",
    }
    T(path).append(long)
    scan = scan_transcript(path)
    assert scan.boundary is not None and scan.boundary.uuid == "a-long"
