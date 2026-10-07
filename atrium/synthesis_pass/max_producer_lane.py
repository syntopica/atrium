"""The Claude Max OAuth lane."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def max_producer_lane() -> ProducerLane:
    """Bind the lane's tokens once; every call reuses them."""
    from atrium.synthesize.max_lane_call import MODEL, max_lane_call
    from atrium.synthesize.max_lane_tokens import max_lane_tokens

    tokens = max_lane_tokens()

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return max_lane_call(tokens, system_text, user_text, tool)

    return ProducerLane(call, MODEL)
