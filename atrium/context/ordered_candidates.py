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
    """Merge the reranked hits by logit, then alternate the ones left in fused order.

    Fused scores are rank fractions of two separate fusions and say nothing
    about which side is stronger, so unscored hits keep the alternation that
    keeps notes from being starved. With no reranker, or none scored, that
    alternation is the whole order.
    """
    if reranked is None or not reranked.get("scored"):
        return interleave_candidates(history, notes, links)
    head = merge_by_score(
        [hit for hit in history if hit.lane == "reranked"],
        [hit for hit in notes if hit.lane == "reranked"],
        links,
    )
    tail = interleave_candidates(
        [hit for hit in history if hit.lane != "reranked"],
        [hit for hit in notes if hit.lane != "reranked"],
        links,
    )
    return head + tail
