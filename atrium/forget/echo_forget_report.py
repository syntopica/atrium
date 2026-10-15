"""Summarize what an echo forget pass would change, before it changes anything."""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def echo_forget_report(
    candidates: Mapping[str, str],
    latest: Mapping[str, Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Count new, already forgotten and restored candidates, by echo."""
    new = {event["record_id"] for event in events}
    return {
        "rule": "harness-echo",
        "candidates": len(candidates),
        "new": len(new),
        "already_forgotten": sum(
            1 for rid in candidates if latest.get(rid, {}).get("event") == "forget"
        ),
        "kept_by_restore": sum(
            1 for rid in candidates if latest.get(rid, {}).get("event") == "restore"
        ),
        "new_by_echo": dict(Counter(candidates[rid] for rid in new).most_common()),
        "applied": False,
    }
