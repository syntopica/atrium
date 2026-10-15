"""Group the logged answers into gaps and the records served most."""

from collections import Counter
from collections.abc import Iterable
from typing import Any

from atrium.gaps.best_score import best_score
from atrium.gaps.is_gap import is_gap
from atrium.gaps.normalized_question import normalized_question


def gap_report(events: Iterable[dict[str, Any]], top: int) -> dict[str, Any]:
    """Return ``gaps`` (most-asked first) and ``served`` (records handed out most).

    A gap is a question to answer in the curated layer: something sessions
    keep asking that nothing on record answers. ``served`` is the other side,
    the memory actually in use, which is what a stale or wrong record costs
    the most in.
    """
    gaps: dict[str, dict[str, Any]] = {}
    served: Counter[str] = Counter()
    answered = 0
    for event in events:
        answered += 1
        for item in event.get("evidence") or []:
            if item.get("record_id"):
                served[item["record_id"]] += 1
        if not is_gap(event):
            continue
        key = normalized_question(str(event.get("query") or ""))
        gap = gaps.setdefault(
            key, {"question": event.get("query"), "asked": 0, "workspaces": [], "best": None}
        )
        gap["asked"] += 1
        gap["last_asked"] = event.get("ts")
        if event.get("workspace") and event["workspace"] not in gap["workspaces"]:
            gap["workspaces"].append(event["workspace"])
        score = best_score(event)
        if score is not None and (gap["best"] is None or score > gap["best"]):
            gap["best"] = score
    ranked = sorted(gaps.values(), key=lambda gap: (-gap["asked"], gap.get("last_asked") or ""))
    return {
        "answers": answered,
        "gaps": ranked[:top],
        "gap_count": len(ranked),
        "served": [{"record_id": rid, "times": n} for rid, n in served.most_common(top)],
    }
