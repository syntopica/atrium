"""The cursor and agy synthesis lanes routed through the worker's task queue."""

import hashlib
import os
import time
from typing import Any

from atrium.synthesize.lane_prompt import LanePrompt
from atrium.synthesize.lane_prompt_text import lane_prompt_text
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.worker_http_call import worker_http_call
from atrium.synthesize.worker_lane_submit import worker_lane_submit

# The worker's queue answers a wall on this profile's runner by running the job
# under the queue's fallback (atrium.agy), so the lane names one profile only.
WORKER_TASK_DEFAULT_PROFILE = "atrium.cursor"

# The largest prompt anything in this stack has been seen to survive: cursor
# returned an empty stdout with exit 0 at 800 KB (clips, 2026-09-11), and agy
# takes the prompt on argv, under macOS's 1 MiB ARG_MAX.
_PROMPT_CEILING_BYTES = 512 * 1024

# The task loop runs one task at a time, so a job waits behind every other job
# in flight. Giving up here loses no work: the next pass re-finds the job by
# its idempotency key and collects the result.
_WAIT_SECONDS = 1800


def worker_task_lane_call(
    prompt_parts: LanePrompt, tool: dict[str, Any], profile: str = WORKER_TASK_DEFAULT_PROFILE
) -> dict[str, Any]:
    """Same contract as cursor_lane_call; the worker owns the runners and their walls.

    A job held while every runner it could use rests (``cooling_until``) raises
    QuotaExhaustedError, so the pass stops submitting and leaves the job queued
    for a later pass to collect. Ack precedes the registry write, the gap the
    inference lane accepts too; the retry-key walk recovers from it.
    """
    schema = {**tool["input_schema"], "additionalProperties": False}
    prompt = lane_prompt_text(prompt_parts, schema)
    if len(prompt.encode("utf-8")) > _PROMPT_CEILING_BYTES:
        raise RuntimeError(f"prompt too large for a task runner ({len(prompt)} chars)")
    key = "task:" + hashlib.sha256((profile + prompt).encode()).hexdigest()
    job = {
        "contract": 1,
        "kind": "task",
        "queue": "atrium.tasks",
        "idempotency_key": key,
        "priority": 40,
        "privacy": "personal",
        "max_attempts": 2,
        "input": {"profile": profile, "prompt": prompt, "output_schema": schema},
    }
    job_id = worker_lane_submit(job)
    poll = float(os.environ.get("ATRIUM_WORKER_POLL", "10"))
    deadline = time.monotonic() + _WAIT_SECONDS
    while time.monotonic() < deadline:
        state = worker_http_call("GET", f"/v1/jobs/{job_id}")
        result = state.get("result")
        if result is None:
            if state.get("cooling_until"):
                raise QuotaExhaustedError(
                    f"worker runners cooling until {int(state['cooling_until'])}"
                )
            time.sleep(poll)
            continue
        worker_http_call(
            "POST", f"/v1/jobs/{job_id}/ack", {"result_id": result["result_id"], "decline": False}
        )
        output = (result.get("output") or {}).get("json")
        if result["control"] is None and isinstance(output, dict):
            executor = result.get("executor") or {}
            runner, model = executor.get("provider", ""), executor.get("model", "")
            usage = result.get("usage") or {}
            return {
                "input": output,
                "model": f"{runner}-{model}" if model else runner,
                "usage": {
                    "input_tokens": usage.get("tokens_in", 0),
                    "output_tokens": usage.get("tokens_out", 0),
                },
            }
        error = (result.get("detail") or {}).get("error", "no JSON object")
        raise RuntimeError(f"worker task ended: {result['control']} ({error})")
    raise RuntimeError("worker task still pending")
