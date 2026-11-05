"""The Claude Code CLI lane returns structured output and stops at a quota wall."""

import json
import subprocess
from collections.abc import Callable
from typing import Any

import pytest

from atrium.synthesize.claude_cli_lane_call import claude_cli_lane_call
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL

_SCHEMA: dict[str, Any] = SYNTHESIS_TOOL["input_schema"]  # type: ignore[assignment]
_REQUIRED = dict.fromkeys(_SCHEMA["required"], "x")


def _stub(
    returncode: int, result: dict[str, Any], seen: list[Any] | None = None
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if seen is not None:
            seen.append((argv, kwargs))
        return subprocess.CompletedProcess(
            args=argv, returncode=returncode, stdout=json.dumps(result), stderr=""
        )

    return run


def test_the_structured_output_is_the_record(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []
    result = {
        "is_error": False,
        "structured_output": _REQUIRED,
        "modelUsage": {"claude-haiku-5-5": {}},
        "usage": {"output_tokens": 3},
    }
    monkeypatch.setattr(subprocess, "run", _stub(0, result, seen))
    answer = claude_cli_lane_call("system", "transcript", SYNTHESIS_TOOL, "claude-haiku-5-5")
    assert answer == {
        "input": _REQUIRED,
        "model": "claude-haiku-5-5",
        "usage": {"output_tokens": 3},
    }
    argv, kwargs = seen[0]
    assert argv[argv.index("--model") + 1] == "claude-haiku-5-5"
    assert "--no-session-persistence" in argv
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "transcript" in kwargs["input"]


def test_a_spent_window_is_a_quota_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    result = {"is_error": True, "result": "Claude usage limit reached. Resets 9pm."}
    monkeypatch.setattr(subprocess, "run", _stub(1, result))
    with pytest.raises(QuotaExhaustedError):
        claude_cli_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_a_rate_limited_request_is_a_quota_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    result = {"is_error": True, "api_error_status": 429, "result": "API Error"}
    monkeypatch.setattr(subprocess, "run", _stub(1, result))
    with pytest.raises(QuotaExhaustedError):
        claude_cli_lane_call("system", "user", SYNTHESIS_TOOL, "m")


def test_other_failures_stay_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", _stub(1, {"is_error": True, "result": "boom"}))
    with pytest.raises(RuntimeError) as caught:
        claude_cli_lane_call("system", "user", SYNTHESIS_TOOL, "m")
    assert not isinstance(caught.value, QuotaExhaustedError)


def test_an_answer_missing_a_required_key_is_not_a_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subprocess, "run", _stub(0, {"structured_output": {}}))
    with pytest.raises(RuntimeError, match="missing required keys"):
        claude_cli_lane_call("system", "user", SYNTHESIS_TOOL, "m")
