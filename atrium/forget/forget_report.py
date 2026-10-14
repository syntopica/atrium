"""Summarize what a forget pass would change, before it changes anything."""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from atrium.context.retirement import Retirement


def forget_report(
    candidates: Mapping[str, tuple[Retirement, str]],
    latest: Mapping[str, Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count new, already forgotten and restored candidates, by term and role."""
    new = {event["record_id"] for event in events}
    pinned = [rid for rid in candidates if latest.get(rid, {}).get("event") == "restore"]
    return {
        "rule": "retired",
        "candidates": len(candidates),
        "new": len(new),
        "already_forgotten": sum(
            1 for rid in candidates if latest.get(rid, {}).get("event") == "forget"
        ),
        "kept_by_restore": len(pinned),
        "new_by_term": dict(Counter(candidates[rid][0].terms[0] for rid in new).most_common()),
        "new_by_role": dict(Counter(candidates[rid][1] for rid in new).most_common()),
        "applied": False,
    }
