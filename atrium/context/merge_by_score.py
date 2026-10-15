"""One candidate order across history and notes, by cross-encoder logit."""

from atrium.context.rerank_floor import RERANK_FLOOR
from atrium.retrieve.hit import Hit


def merge_by_score(
    history: list[Hit], notes: list[Hit], links: list[tuple[Hit, str]]
) -> list[tuple[Hit, str, str | None]]:
    """Order reranked candidates by logit, each note followed by its links.

    Only for reranked populations: their scores are logits on one scale, so a
    strong note can outrank a weak transcript and the reverse, where the
    alternation gives each side every other slot whatever it scored. Measured
    2026-10-15: note questions' MRR 0.47 to 0.57 (holdout) and 0.25 to 0.34
    (acceptance), conversation questions 0.41 to 0.40 and 0.25 to 0.25, recall
    unchanged on both. Candidates below ``RERANK_FLOOR`` are not evidence.
    Equal logits keep history first, then the incoming order.
    """
    tagged = [(hit, "history") for hit in history] + [(hit, "curated") for hit in notes]
    kept = [one for one in tagged if one[0].score >= RERANK_FLOOR]
    ordered = sorted(enumerate(kept), key=lambda pair: (-pair[1][0].score, pair[0]))
    candidates: list[tuple[Hit, str, str | None]] = []
    for _, (hit, via) in ordered:
        candidates.append((hit, via, None))
        if via == "curated":
            candidates.extend(
                (link, "link", parent) for link, parent in links if parent == hit.record_id
            )
    return candidates
