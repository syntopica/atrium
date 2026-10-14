"""Turn retired candidates into the forget events the ledger still lacks."""

from collections.abc import Mapping
from typing import Any

from atrium.context.retirement import Retirement


def retired_forget_events(
    candidates: Mapping[str, tuple[Retirement, str]],
    latest: Mapping[str, Mapping[str, Any]],
    today: str,
) -> list[dict[str, Any]]:
    """Return one event per candidate with no event yet.

    A record already forgotten needs nothing, and one whose latest event is a
    restore is pinned: the owner brought it back, and a rule rerun must not
    undo that.
    """
    return [
        {
            "event": "forget",
            "record_id": record_id,
            "rule": "retired",
            "rule_version": 1,
            "detail": retirement.terms[0],
            "at": today,
        }
        for record_id, (retirement, _) in sorted(candidates.items())
        if record_id not in latest
    ]
