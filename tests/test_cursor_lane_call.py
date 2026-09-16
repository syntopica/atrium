"""The cursor lane reads one envelope and treats a spent window as a wall."""

import json
import os
import signal
import subprocess
from typing import Any

import pytest

from atrium.synthesize.cursor_lane_call import cursor_lane_call
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL

_OUTPUT = {"title": "t", "summary": "s", "facts": ["f"], "open_ends": []}


class _FakeProcess:
    """What `subprocess.Popen` hands back, without a process."""

    pid = 4242

    def __init__(self, stdout: str, returncode: int, stderr: str) -> None:
        self._out = (stdout, stderr)
        self.returncode = returncode
        self.received: str | None = None

    def communicate(self, prompt: str, timeout: float) -> tuple[str, str]:
        self.received = prompt
        return self._out


def _stub(stdout: str, returncode: int = 0, stderr: str = ""):
    calls: list[dict[str, Any]] = []

    def popen(args: list[str], **kwargs: Any) -> _FakeProcess:
        process = _FakeProcess(stdout, returncode, stderr)
        calls.append({"args": args, "process": process, **kwargs})
        return process

    popen.calls = calls  # type: ignore[attr-defined]
    return popen


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
    monkeypatch.setattr(subprocess, "Popen", run)
    result = cursor_lane_call("system", "user", SYNTHESIS_TOOL, "gemini-3.7-flash-high")
    assert result["input"] == _OUTPUT
    assert result["model"] == "gemini-3.7-flash-high"
    assert result["usage"] == {"input_tokens": 24627, "output_tokens": 9}


def test_the_prompt_rides_on_stdin_in_read_only_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _stub(_envelope(json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "Popen", run)
    cursor_lane_call("SYSTEM", "TRANSCRIPT", SYNTHESIS_TOOL, "m")
    call = run.calls[0]
    prompt = call["process"].received
    assert call["args"][:3] == ["cursor-agent", "-p", "--mode"]
    assert "ask" in call["args"] and "--force" not in call["args"]
    assert "TRANSCRIPT" in prompt and "SYSTEM" in prompt
    # Instructions before the transcript: a transcript that is itself an
    # imperative outranked instructions placed after it on the first pass.
    assert prompt.index("SYSTEM") < prompt.index("TRANSCRIPT")
    assert not any("TRANSCRIPT" in part for part in call["args"])


def test_the_cli_runs_in_its_own_session_and_the_group_is_killed_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One hour of the drip left 38 orphaned worker-servers holding 7.4 GB."""
    run = _stub(_envelope(json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "Popen", run)
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: killed.append((pgid, sig)))
    cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")
    assert run.calls[0]["start_new_session"] is True
    assert killed == [(4242, signal.SIGTERM)]


def test_the_group_is_killed_even_when_the_call_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "Popen", _stub("", returncode=1, stderr="boom"))
    killed: list[int] = []
    monkeypatch.setattr(os, "killpg", lambda pgid, sig: killed.append(pgid))
    with pytest.raises(RuntimeError):
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")
    assert killed == [4242]


def test_a_usage_limit_is_a_quota_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    error = _envelope("You have hit your usage limit for this month.", is_error=True)
    monkeypatch.setattr(subprocess, "Popen", _stub(error))
    with pytest.raises(QuotaExhaustedError):
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_empty_stdout_with_exit_zero_is_a_plain_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "Popen", _stub(""))
    with pytest.raises(RuntimeError) as caught:
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")
    assert not isinstance(caught.value, QuotaExhaustedError)


def test_a_missing_required_key_is_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "Popen", _stub(_envelope('{"title": "only"}')))
    with pytest.raises(RuntimeError, match="missing required keys"):
        cursor_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_an_oversized_prompt_never_reaches_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    run = _stub(_envelope(json.dumps(_OUTPUT)))
    monkeypatch.setattr(subprocess, "Popen", run)
    with pytest.raises(RuntimeError, match="too large"):
        cursor_lane_call("system", "x" * (600 * 1024), SYNTHESIS_TOOL, "m")
    assert run.calls == []
