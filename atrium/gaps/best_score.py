"""The best reranked score an answer carried, or None when it was not reranked."""

from typing import Any


def best_score(event: dict[str, Any]) -> float | None:
    """Return the highest reranked score, or None when no score is comparable.

    Only a reranked hit's score is a cross-encoder logit; a fused hit's is a
    rank fraction and a linked note's has no meaning across questions, so an
    answer with no reranked evidence cannot say whether its evidence was good.
    """
    scores = [
        item["score"]
        for item in event.get("evidence") or []
        if item.get("lane") == "reranked" and isinstance(item.get("score"), int | float)
    ]
    return max(scores) if scores else None
