"""Whether one logged answer left its question unanswered."""

from typing import Any

from atrium.gaps.best_score import best_score
from atrium.gaps.gap_score_threshold import GAP_SCORE_THRESHOLD


def is_gap(event: dict[str, Any]) -> bool:
    """True for a read index that returned nothing, or nothing scoring as an answer.

    A failed or unreadable index is an outage, not a gap: it says nothing
    about what the memory holds.
    """
    if event.get("index_status") not in ("ready", "empty"):
        return False
    if not event.get("evidence"):
        return True
    score = best_score(event)
    return score is not None and score < GAP_SCORE_THRESHOLD
