"""Reorder one population's fused candidates by cross-encoder score."""

import time
from typing import TYPE_CHECKING

from atrium.retrieve.hit import Hit

if TYPE_CHECKING:
    from atrium.context.context_reranker import ContextReranker


def rerank_hits(
    reranker: "ContextReranker", query: str, hits: list[Hit], budget_s: float
) -> tuple[list[Hit], bool]:
    """Return the hits reordered, and whether the reranker answered.

    The candidate set never changes, only its order. Equal scores keep the
    fused order, so the result is the same on every machine. A reranker that
    fails or runs past ``budget_s`` leaves the fused order as it was.
    """
    if len(hits) < 2:  # noqa: PLR2004 -- nothing to reorder
        return hits, True
    try:
        scores = reranker.score(query, [hit.text for hit in hits], time.monotonic() + budget_s)
    except (TimeoutError, RuntimeError, OSError, ValueError):
        return hits, False
    if len(scores) != len(hits):
        return hits, False
    order = sorted(range(len(hits)), key=lambda index: (-scores[index], index))
    return [hits[index] for index in order], True
