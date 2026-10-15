"""The candidate order evidence selection walks, by how the populations were scored."""

from typing import Any

from atrium.context.interleave_candidates import interleave_candidates
from atrium.context.merge_by_score import merge_by_score
from atrium.retrieve.hit import Hit


def ordered_candidates(
    history: list[Hit],
    notes: list[Hit],
    links: list[tuple[Hit, str]],
    reranked: dict[str, Any] | None,
) -> list[tuple[Hit, str, str | None]]:
    """Merge by logit when both populations were reranked, else alternate them.

    Fused scores are rank fractions of two separate fusions and say nothing
    about which side is stronger, so without a reranker the alternation that
    keeps notes from being starved stays.
    """
    if reranked is not None and reranked["applied"]:
        return merge_by_score(history, notes, links)
    return interleave_candidates(history, notes, links)
