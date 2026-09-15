"""Complete response warnings after all retrieval passes have finished."""

from typing import Any


def finalize_context(response: dict[str, Any]) -> dict[str, Any]:
    """Make empty, bounded, and degraded outcomes explicit."""
    if any(step["candidates"] == step["candidate_limit"] for step in response["steps"]):
        response["truncated"] = True
        response["warnings"].append("retrieval_candidate_limit_reached")
    if response["index_status"] == "empty":
        response["warnings"].append("index_empty")
    if not response["evidence"] and response["index_status"] != "unavailable":
        response["warnings"].append("no_matches")
    response["degraded"] = any(warning != "no_matches" for warning in response["warnings"])
    return response
