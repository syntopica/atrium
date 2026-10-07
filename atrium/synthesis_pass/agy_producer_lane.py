"""The Antigravity (agy) lane: Gemini bulk quota, the default."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def agy_producer_lane(model: str | None) -> ProducerLane:
    """Use ``model`` or the lane default."""
    from atrium.synthesize.agy_lane_call import AGY_MODEL_ID, agy_lane_call
    from atrium.synthesize.agy_lane_model_id import agy_lane_model_id

    agy_model = model or AGY_MODEL_ID

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return agy_lane_call(system_text, user_text, tool, agy_model)

    return ProducerLane(call, agy_lane_model_id(agy_model))
