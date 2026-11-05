"""The Claude Code CLI lane."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def claude_producer_lane(model: str | None) -> ProducerLane:
    """Pin the Claude model for the whole pass; the model id is the population."""
    from atrium.synthesize.claude_cli_default_model import CLAUDE_CLI_DEFAULT_MODEL
    from atrium.synthesize.claude_cli_lane_call import claude_cli_lane_call

    claude_model = model or CLAUDE_CLI_DEFAULT_MODEL

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return claude_cli_lane_call(system_text, user_text, tool, claude_model)

    return ProducerLane(call, claude_model)
