"""The local lane hands Ollama the schema as a grammar, not only as prose."""

import io
import json
from typing import Any

import pytest

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.local_lane_call import local_lane_call
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL

_OUTPUT = {"title": "t", "summary": "s", "facts": ["f"], "open_ends": []}


def _stub(monkeypatch: pytest.MonkeyPatch, content: str) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    class _Response(io.BytesIO):
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def urlopen(request: Any, timeout: float) -> _Response:
        sent.append(json.loads(request.data))
        answer = {"message": {"content": content}, "prompt_eval_count": 7, "eval_count": 3}
        return _Response(json.dumps(answer).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return sent


def test_the_request_carries_the_schema_as_a_grammar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only `format` binds the sampler; the prompt copy is what an MLX build gets."""
    sent = _stub(monkeypatch, json.dumps(_OUTPUT))
    local_lane_call(LanePrompt("system", "transcript"), SYNTHESIS_TOOL)
    assert sent[0]["format"]["additionalProperties"] is False
    assert sent[0]["format"]["required"] == SYNTHESIS_TOOL["input_schema"]["required"]


def test_an_answer_missing_a_required_key_is_not_a_record(monkeypatch: pytest.MonkeyPatch) -> None:
    """Measured: an unconstrained model returns exactly this, and the job is lost."""
    _stub(monkeypatch, json.dumps({"title": "t"}))
    with pytest.raises(RuntimeError, match="missing required keys"):
        local_lane_call(LanePrompt("system", "transcript"), SYNTHESIS_TOOL)
