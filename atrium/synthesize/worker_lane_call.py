"""The local synthesis lane routed through the worker queue instead of Ollama directly."""

import hashlib
import os
import time
from collections.abc import Callable
from typing import Any

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.lane_prompt_text import lane_prompt_text
from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL
from atrium.synthesize.worker_http_call import worker_http_call
from atrium.synthesize.worker_lane_submit import worker_lane_submit

# Under the drip's 1800 s stall guard: a pending job is re-found by its
# idempotency key on the next pass, so giving up here loses no work.
_WAIT_SECONDS = 1500

WORKER_SYNTHESIS_QUEUE = "atrium.synthesis"


def worker_lane_call(
    prompt_parts: LanePrompt,
    tool: dict[str, Any],
    model: str = LOCAL_DEFAULT_MODEL,
    on_submit: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Same contract as local_lane_call; the worker owns idle gating and the Ollama options.

    A usable result is returned unacknowledged, under ``worker_results``: the
    caller acks it only after its registry holds the record, so a crash in
    between leaves the result for the next pass instead of losing it.
    """
    schema = {**tool["input_schema"], "additionalProperties": False}
    prompt = lane_prompt_text(prompt_parts, schema)
    key = "syn:" + hashlib.sha256((model + prompt).encode()).hexdigest()
    job = {
        "contract": 1,
        "kind": "inference",
        "queue": WORKER_SYNTHESIS_QUEUE,
        "idempotency_key": key,
        "priority": 40,
        "privacy": "personal",
        "max_attempts": 2,
        "requirements": {"capability": "chat.json", "models": [model]},
        "input": {
            "messages": [{"role": "user", "content": prompt}],
            "schema": schema,
            "options": {"temperature": 0.2},
        },
    }
    job_id = worker_lane_submit(job)
    if on_submit is not None:
        on_submit(job_id)
    poll = float(os.environ.get("ATRIUM_WORKER_POLL", "10"))
    deadline = time.monotonic() + _WAIT_SECONDS
    while time.monotonic() < deadline:
        state = worker_http_call("GET", f"/v1/jobs/{job_id}")
        result = state.get("result")
        ack = f"/v1/jobs/{job_id}/ack"
        if result and result["control"] == "split_requested":
            worker_http_call("POST", ack, {"result_id": result["result_id"], "decline": True})
        elif result and result["control"] is None:
            usage = result.get("usage") or {}
            # The worker may answer from OpenRouter or a runner instead of the
            # requested local model, so the record names the executor that did;
            # without one it is unknown, never the model that was only asked for.
            executor = result.get("executor") or {}
            runner, resolved = executor.get("provider", ""), executor.get("model", "")
            return {
                "input": result["output"]["json"],
                "model": f"{runner}-{resolved}" if runner and resolved else "unknown",
                "usage": {
                    "input_tokens": usage.get("tokens_in", 0),
                    "output_tokens": usage.get("tokens_out", 0),
                },
                "worker_results": [{"job_id": job_id, "result_id": result["result_id"]}],
            }
        elif result:
            worker_http_call("POST", ack, {"result_id": result["result_id"], "decline": False})
            raise RuntimeError(f"worker job ended: {result['control']}")
        time.sleep(poll)
    raise RuntimeError("worker job still pending")
