"""The agy lane routed through the worker's atrium.tasks queue."""

from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def task_producer_lane(model: str | None) -> ProducerLane:
    """``model`` names the worker profile."""
    from atrium.synthesize.lane_prompt import LanePrompt
    from atrium.synthesize.worker_task_lane_call import (
        WORKER_TASK_DEFAULT_PROFILE,
        WORKER_TASK_QUEUE,
        worker_task_lane_call,
    )
    from atrium.synthesize.worker_task_lane_model_id import worker_task_lane_model_id

    task_profile = model or WORKER_TASK_DEFAULT_PROFILE

    def journaled_call(
        system_text: str, user_text: str, tool: dict[str, Any], on_submit: Any
    ) -> dict[str, Any]:
        return worker_task_lane_call(
            LanePrompt(system_text, user_text), tool, task_profile, on_submit
        )

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return journaled_call(system_text, user_text, tool, None)

    return ProducerLane(
        call, worker_task_lane_model_id(task_profile), journaled_call, WORKER_TASK_QUEUE
    )
