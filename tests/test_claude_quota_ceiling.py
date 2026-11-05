"""The Claude lane yields once the account's fullest usage window reaches the ceiling."""

from typing import Any

import pytest

import atrium.synthesize.claude_cli_lane_call as lane_call
from atrium.synthesis_pass.claude_producer_lane import claude_producer_lane
from atrium.synthesize.claude_quota_ceiling import CLAUDE_QUOTA_CEILING
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.synthesis_schema import SYNTHESIS_TOOL


def _answers(utilizations: list[float | None], calls: list[int]) -> Any:
    def fake(system_text: str, user_text: str, tool: Any, model: str) -> dict[str, Any]:
        calls.append(1)
        return {"input": {}, "model": model, "usage": {}, "utilization": utilizations.pop(0)}

    return fake


def test_a_call_after_the_ceiling_is_refused_without_spending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        lane_call, "claude_cli_lane_call", _answers([0.5, CLAUDE_QUOTA_CEILING], calls)
    )
    lane = claude_producer_lane(None)
    lane.call("s", "u", SYNTHESIS_TOOL)
    lane.call("s", "u", SYNTHESIS_TOOL)
    with pytest.raises(QuotaExhaustedError, match="ceiling"):
        lane.call("s", "u", SYNTHESIS_TOOL)
    assert len(calls) == 2


def test_an_unreported_window_never_stops_the_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(lane_call, "claude_cli_lane_call", _answers([None, None, None], calls))
    lane = claude_producer_lane(None)
    for _ in range(3):
        lane.call("s", "u", SYNTHESIS_TOOL)
    assert len(calls) == 3
