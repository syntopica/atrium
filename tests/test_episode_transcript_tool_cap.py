"""Tool traffic reaches the synthesis model as head and tail, conversation whole."""

from atrium.synthesize.episode_transcript import episode_transcript
from atrium.synthesize.tool_output_char_cap import TOOL_OUTPUT_CHAR_CAP

_LONG = "q" * (TOOL_OUTPUT_CHAR_CAP * 3)


def _event(role: str | None, text: str, kind: str = "message") -> dict:
    return {"kind": kind, "role": role, "text": text}


def _rendered(events: list[dict]) -> str:
    return episode_transcript(list(range(len(events))), events)


def test_a_long_tool_result_keeps_its_head_and_tail() -> None:
    text = "HEAD" + _LONG + "TAIL"
    out = _rendered([_event("user", "run it"), _event("tool", text)])
    assert "HEAD" in out
    assert "TAIL" in out
    assert "[... truncated for synthesis ...]" in out
    assert len(out) < TOOL_OUTPUT_CHAR_CAP + 200


def test_a_codex_exec_output_without_a_role_is_capped() -> None:
    out = _rendered([_event("user", "run it"), _event(None, "Script completed " + _LONG)])
    assert len(out) < TOOL_OUTPUT_CHAR_CAP + 200


def test_a_rendered_result_under_the_user_role_is_capped() -> None:
    events = [
        _event("user", "list the files"),
        _event("assistant", "tool: Bash\nls -R /"),
        _event("user", _LONG),
    ]
    assert len(_rendered(events)) < TOOL_OUTPUT_CHAR_CAP + 200


def test_human_and_assistant_prose_stay_whole() -> None:
    prose = "y" * (TOOL_OUTPUT_CHAR_CAP * 3)
    out = _rendered([_event("user", prose), _event("assistant", prose)])
    assert out.count("y") == 2 * len(prose)
    assert "truncated" not in out


def test_a_short_tool_result_is_untouched() -> None:
    out = _rendered([_event("user", "go"), _event("tool", "exit 0")])
    assert out == "[user] go\n[tool] exit 0"


def test_a_document_read_stays_whole() -> None:
    events = [
        _event("user", "read the transcript"),
        _event("assistant", "tool: Read\n/tmp/notes.txt"),
        _event("tool", _LONG),
    ]
    assert _rendered(events).count("q") == len(_LONG)


def test_parallel_calls_are_answered_in_order() -> None:
    events = [
        _event("user", "look"),
        _event("assistant", "tool: Bash\ntool: Read"),
        _event("tool", "\u0416" * len(_LONG)),
        _event("tool", "\u03a9" * len(_LONG)),
    ]
    out = _rendered(events)
    assert out.count("\u0416") <= TOOL_OUTPUT_CHAR_CAP
    assert out.count("\u03a9") == len(_LONG)
