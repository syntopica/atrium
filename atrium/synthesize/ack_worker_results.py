"""Acknowledge worker results once the registry holds what they produced."""

from typing import Any

from atrium.synthesize.worker_http_call import worker_http_call


def ack_worker_results(results: list[dict[str, Any]]) -> None:
    """Ack each ``{"job_id", "result_id"}``; acking a result twice is harmless."""
    for result in results:
        worker_http_call(
            "POST",
            f"/v1/jobs/{result['job_id']}/ack",
            {"result_id": result["result_id"], "decline": False},
        )
