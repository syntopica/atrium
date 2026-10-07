"""The local-model lane, direct to Ollama or through the worker's queue."""

import os
from typing import Any

from atrium.synthesis_pass.producer_lane import ProducerLane


def local_producer_lane(model: str | None) -> ProducerLane:
    """``ATRIUM_LOCAL_TRANSPORT=worker`` routes the calls through the worker queue."""
    from atrium.synthesize.lane_prompt import LanePrompt
    from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL, local_lane_call
    from atrium.synthesize.local_lane_model_id import local_lane_model_id

    local_model = model or LOCAL_DEFAULT_MODEL
    model_id = local_lane_model_id(local_model)

    if os.environ.get("ATRIUM_LOCAL_TRANSPORT") == "worker":
        from atrium.synthesize.worker_lane_call import WORKER_SYNTHESIS_QUEUE, worker_lane_call

        def journaled_call(
            system_text: str, user_text: str, tool: dict[str, Any], on_submit: Any
        ) -> dict[str, Any]:
            return worker_lane_call(
                LanePrompt(system_text, user_text), tool, local_model, on_submit
            )

        def worker_call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
            return journaled_call(system_text, user_text, tool, None)

        return ProducerLane(worker_call, model_id, journaled_call, WORKER_SYNTHESIS_QUEUE)

    def call(system_text: str, user_text: str, tool: dict[str, Any]) -> dict[str, Any]:
        return local_lane_call(LanePrompt(system_text, user_text), tool, local_model)

    return ProducerLane(call, model_id)
