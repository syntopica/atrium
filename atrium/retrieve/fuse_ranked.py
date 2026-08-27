"""Weighted reciprocal-rank fusion of the lexical and dense lanes."""

from dataclasses import replace

from atrium.retrieve.hit import Hit

# Swept 0-100% dense in 5% steps with five-fold cross-validation on a 389-pair
# set from this corpus: 30% dense / 70% lexical won four of five folds
# (R@10 80.0% / MRR 0.635 vs 77.3% / 0.580 for lexical alone). Re-measure
# before changing either number.
_K = 60
_LEXICAL_WEIGHT = 0.7


def fuse_ranked(lexical: list[Hit], dense: list[Hit], limit: int = 20) -> list[Hit]:
    """Merge two ranked lists by weighted RRF, higher fused score first.

    Callers must not treat this as the only output: on queries sharing no
    informative word with their answer, fusion demotes the dense signal that is
    the only one working (12% -> 8% R@10 measured). The adaptive routing that
    honours that lives in ``search_hybrid``; this function only fuses.
    """
    scores: dict[str, float] = {}
    first_seen: dict[str, Hit] = {}
    for weight, hits in ((_LEXICAL_WEIGHT, lexical), (1.0 - _LEXICAL_WEIGHT, dense)):
        for rank, hit in enumerate(hits, start=1):
            scores[hit.record_id] = scores.get(hit.record_id, 0.0) + weight / (_K + rank)
            first_seen.setdefault(hit.record_id, hit)
    # record_id breaks score ties so equal-score fusions rank identically on
    # every machine, whatever order the lanes delivered their hits in.
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [
        replace(first_seen[record_id], score=score, lane="fused") for record_id, score in ranked
    ]
