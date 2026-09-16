"""The cursor lane reads one envelope and treats a spent window as a wall."""

import json
import subprocess
from typing import Any

import pytest

from atrium.synthesize.cursor_lane_call import cursor_lane_call
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL

_OUTPUT = {"title": "t", "summary": "s", "facts": ["f"], "open_ends": []}


def _stub(stdout: str, returncode: int = 0, stderr: str = ""):
    calls: list[dict[str, Any]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"args": args, **kwargs})
        return subprocess.CompletedProcess(
            args=args, returncode=returncode, stdout=stdout, stderr=stderr
        )

    run.calls = calls  # type: ignore[attr-defined]
    return run


def _envelope(result: str, **extra: Any) -> str:
    return json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": result,
            "usage": {"inputTokens": 24627, "outputTokens": 9},
            **extra,
        }
    )


def test_the_answer_is_read_from_the_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _stub(_envelope("Here it is.\n" + json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "run", run)
    result = cursor_lane_call("system", "user", SYNTHESIS_TOOL, "gemini-3.7-flash-high")
    assert result["input"] == _OUTPUT
    assert result["model"] == "gemini-3.7-flash-high"
    assert result["usage"] == {"input_tokens": 24627, "output_tokens": 9}


def test_the_prompt_rides_on_stdin_in_read_only_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _stub(_envelope(json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "run", run)
    cursor_lane_call("SYSTEM", "TRANSCRIPT", SYNTHESIS_TOOL, "m")
    call = run.calls[0]
    assert call["args"][:3] == ["cursor-agent", "-p", "--mode"]
    assert "ask" in call["args"] and "--force" not in call["args"]
    assert "TRANSCRIPT" in call["input"] and "SYSTEM" in call["input"]
    # Instructions before the transcript: a transcript that is itself an
    # imperative outranked instructions placed after it on the first pass.
    assert call["input"].index("SYSTEM") < call["input"].index("TRANSCRIPT")
    assert not any("TRANSCRIPT" in part for part in call["args"])


def test_a_usage_limit_is_a_quota_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _envelope("You have hit your usage limit for this month.", is_error=True)
    monkeypatch.setattr(subprocess, "run", _stub(error))
    with pytest.raises(QuotaExhaustedError):
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_empty_stdout_with_exit_zero_is_a_plain_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _stub(""))
    with pytest.raises(RuntimeError) as caught:
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")
    assert not isinstance(caught.value, QuotaExhaustedError)


def test_a_missing_required_key_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _stub(_envelope('{"title": "only"}')))
    with pytest.raises(RuntimeError, match="missing required keys"):
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_an_oversized_prompt_never_reaches_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _stub(_envelope(json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(RuntimeError, match="too large"):
        cursor_lane_call("system", "x" * (600 * 1024), SYNTHESIS_TOOL, "m")
    assert run.calls == []
