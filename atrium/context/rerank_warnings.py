"""What an answer says about a rerank that did not score every candidate."""

from typing import Any


def rerank_warnings(step: dict[str, Any]) -> list[str]:
    """Name a rerank that scored nothing, or one cut short with a fused tail."""
    if not step["scored"]:
        return ["rerank_unavailable_fused_order"]
    if not step["applied"]:
        return ["rerank_partial_fused_tail"]
    return []
