"""Rerank the history and curated candidates of one answer under one shared budget."""

import time
from typing import TYPE_CHECKING, Any

from atrium.context.rerank_budget_s import RERANK_BUDGET_S
from atrium.context.rerank_hits import rerank_hits
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

    Each population is reordered within itself, so neither crowds the other
    out of the interleaving that follows. If either rerank fails, both
    populations retain their original fused order.
    """
    history, notes = populations
    started = time.monotonic()
    history, history_ok = rerank_hits(reranker, query, history, budget_s)
    remaining = budget_s - (time.monotonic() - started)
    notes, notes_ok = rerank_hits(reranker, query, notes, remaining)
    if not history_ok or not notes_ok:
        history, notes = populations
    step = {
        "pass": "rerank",
        "candidates": len(history) + len(notes),
        "candidate_limit": depth * 2,
        "applied": history_ok and notes_ok,
        "ms": round((time.monotonic() - started) * 1000),
    }
    return history, notes, step
