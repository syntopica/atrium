"""Put one population's scored hits first, by logit, and leave the rest in fused order."""

from dataclasses import replace

from atrium.retrieve.hit import Hit


def reorder_scored(hits: list[Hit], scores: dict[str, float]) -> list[Hit]:
    """Scored hits carry their logit and lane ``reranked``; equal logits keep the fused order.

    The logit, unlike a fused rank score, is comparable across questions, which
    is what the floor and the query log's gap detection read; an unscored hit
    keeps its fused score and lane, so neither mistakes it for a logit.
    """
    scored = sorted(
        (index for index, hit in enumerate(hits) if hit.record_id in scores),
        key=lambda index: (-scores[hits[index].record_id], index),
    )
    head = [
        replace(hits[index], score=scores[hits[index].record_id], lane="reranked")
        for index in scored
    ]
    return head + [hit for hit in hits if hit.record_id not in scores]
