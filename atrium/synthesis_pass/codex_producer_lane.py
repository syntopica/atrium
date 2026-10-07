"""The Codex CLI lane."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def codex_producer_lane(model: str | None, effort: str | None) -> ProducerLane:
    """Pin the Codex model and reasoning effort for the whole pass."""
    from atrium.synthesize.codex_lane_call import codex_lane_call
    from atrium.synthesize.codex_lane_model_id import codex_lane_model_id

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return codex_lane_call(system_text, user_text, tool, model, effort)

    return ProducerLane(call, codex_lane_model_id(model, effort))
