"""Score candidates one at a time until the reranker's deadline passes."""

from typing import TYPE_CHECKING

from atrium.retrieve.hit import Hit

if TYPE_CHECKING:
    from atrium.context.context_reranker import ContextReranker


def score_until_deadline(
    reranker: "ContextReranker", query: str, hits: list[Hit], deadline: float
) -> dict[str, float]:
    """Return the logit of every hit scored before the deadline, by record id.

    Stops at the first timeout or failure and keeps what was scored: under load
    the whole rerank never fits, and discarding the finished head left the
    fused order, acceptance MRR 0.090 against 0.245 for the first 16 scored
    (2026-11-06, ``partial-rerank-2026-11-06``).
    """
    scores: dict[str, float] = {}
    for hit in hits:
        try:
            answer = reranker.score(query, [hit.text], deadline)
        except (TimeoutError, RuntimeError, OSError, ValueError):
            break
        if len(answer) != 1:
            break
        scores[hit.record_id] = answer[0]
    return scores
