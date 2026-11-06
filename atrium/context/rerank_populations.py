"""Rerank the history and curated candidates of one answer under one shared budget."""

import time
from typing import TYPE_CHECKING, Any

from atrium.context.interleaved_hits import interleaved_hits
from atrium.context.reorder_scored import reorder_scored
from atrium.context.rerank_budget_s import RERANK_BUDGET_S
from atrium.context.score_until_deadline import score_until_deadline
from atrium.retrieve.hit import Hit

if TYPE_CHECKING:
    from atrium.context.context_reranker import ContextReranker


def rerank_populations(
    reranker: "ContextReranker",
    query: str,
    populations: tuple[list[Hit], list[Hit]],
    depth: int,
    budget_s: float = RERANK_BUDGET_S,
) -> tuple[list[Hit], list[Hit], dict[str, Any]]:
    """Return the reordered history and notes, and the rerank step to report.

    The budget is spent alternating one history hit and one note, best fused
    first, so a rerank cut short has scored the head of both. Each population
    is reordered within itself: what was scored first by logit, the rest in
    fused order. ``applied`` says every candidate was scored, ``scored`` how many.
    """
    history, notes = populations
    started = time.monotonic()
    scores = score_until_deadline(
        reranker, query, interleaved_hits(history, notes), started + budget_s
    )
    step = {
        "pass": "rerank",
        "candidates": len(history) + len(notes),
        "candidate_limit": depth * 2,
        "applied": len(scores) == len(history) + len(notes),
        "scored": len(scores),
        "ms": round((time.monotonic() - started) * 1000),
    }
    return reorder_scored(history, scores), reorder_scored(notes, scores), step
