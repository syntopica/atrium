"""Submit a worker job under the first retry key that no terminal job already holds."""

from typing import Any

from atrium.synthesize.worker_http_call import worker_http_call

_FAILED_STATES = (
    "failed",
    "cancelled",
    "expired",
    "unacked_expired",
    "superseded",
)
# Four failures exhaust a job, as before. A key can also be spent by a
# *success* whose result someone already acked: the key hashes model and prompt,
# so another conversation carrying the same chunk text consumed it, and that is
# no failure of this content. Seven conversations sharing one 46-character
# chunk burned all four keys that way and then failed every pass (2026-10-09).
# Those walk on without spending the budget, up to eight keys in all.
_FAILURE_BUDGET = 4
_KEYS = 8


def worker_lane_submit(job: dict[str, Any]) -> str:
    """Return the id of a live job for this content, walking past consumed keys."""
    base = job["idempotency_key"]
    failures = 0
    for index in range(_KEYS):
        suffix = f":r{index}" if index else ""
        posted = worker_http_call("POST", "/v1/jobs", {**job, "idempotency_key": base + suffix})
        job_id = str(posted["id"])
        state = worker_http_call("GET", f"/v1/jobs/{job_id}")
        if state.get("result") is not None or state.get("state") not in (
            *_FAILED_STATES,
            "succeeded",
        ):
            return job_id
        if state.get("state") in _FAILED_STATES:
            failures += 1
            if failures >= _FAILURE_BUDGET:
                break
    raise RuntimeError("worker job retries exhausted")
