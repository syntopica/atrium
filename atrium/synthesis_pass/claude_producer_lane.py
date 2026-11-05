"""The Claude Code CLI lane."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def claude_producer_lane(model: str | None) -> ProducerLane:
    """Pin the Claude model for the whole pass; the model id is the population.

    Each answer reports how full the account's usage windows are; once the
    fullest reaches the ceiling, every later call raises the quota wall, so
    the pass stops and its remaining conversations stay pending.
    """
    from atrium.synthesize.claude_cli_default_model import CLAUDE_CLI_DEFAULT_MODEL
    from atrium.synthesize.claude_cli_lane_call import claude_cli_lane_call
    from atrium.synthesize.refuse_over_ceiling import refuse_over_ceiling

    claude_model = model or CLAUDE_CLI_DEFAULT_MODEL
    seen: dict[str, float | None] = {"utilization": None}

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        refuse_over_ceiling(seen["utilization"])
        answer = claude_cli_lane_call(system_text, user_text, tool, claude_model)
        seen["utilization"] = answer["utilization"]
        return answer

    return ProducerLane(call, claude_model)
