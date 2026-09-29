"""Submit a worker job under the first retry key that no terminal job already holds."""

from typing import Any

from atrium.synthesize.worker_http_call import worker_http_call

_SUFFIXES = ("", ":r1", ":r2", ":r3")
_TERMINAL_STATES = (
    "succeeded",
    "failed",
    "cancelled",
    "expired",
    "unacked_expired",
    "superseded",
)


def worker_lane_submit(job: dict[str, Any]) -> str:
    """Return the id of a live job for this content, walking past consumed keys."""
    base = job["idempotency_key"]
    for suffix in _SUFFIXES:
        posted = worker_http_call("POST", "/v1/jobs", {**job, "idempotency_key": base + suffix})
        job_id = str(posted["id"])
        state = worker_http_call("GET", f"/v1/jobs/{job_id}")
        if state.get("result") is None and state.get("state") in _TERMINAL_STATES:
            continue
        return job_id
    raise RuntimeError("worker job retries exhausted")
