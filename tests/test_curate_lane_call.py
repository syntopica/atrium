"""A curation call goes to Codex only when the model says so."""

from typing import Any

import pytest

import atrium.curate.curate_lane_call as module
from atrium.curate.curate_lane_call import curate_lane_call
from atrium.synthesize.lane_prompt import LanePrompt

PROMPT = LanePrompt("system", "the claim", "answer now", "FACT")


def test_an_ollama_name_stays_local(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(module, "local_lane_call", lambda p, t, model: seen.append(model) or {})
    curate_lane_call(PROMPT, {}, "qwen3.6:35b")
    assert seen == ["qwen3.6:35b"]


def test_codex_gets_the_fenced_claim_and_the_named_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        module,
        "codex_lane_call",
        lambda s, u, t, model, effort: calls.append((s, u, model, effort)) or {},
    )
    curate_lane_call(PROMPT, {}, "codex")
    curate_lane_call(PROMPT, {}, "codex:gpt-6.1-sol")
    assert calls[0][0] == "system" and "=== BEGIN FACT ===\nthe claim" in calls[0][1]
    assert [(c[2], c[3]) for c in calls] == [(None, "low"), ("gpt-6.1-sol", "low")]
