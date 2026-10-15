"""Turn echo candidates into the forget events the ledger still lacks."""

from collections.abc import Mapping
from typing import Any


def echo_forget_events(
    candidates: Mapping[str, str], latest: Mapping[str, Mapping[str, Any]], today: str
) -> list[dict[str, Any]]:
    """Return one event per candidate with no event yet; a restore pins a record."""
    return [
        {
            "event": "forget",
            "record_id": record_id,
            "rule": "harness-echo",
            "rule_version": 1,
            "detail": echo,
            "at": today,
        }
        for record_id, echo in sorted(candidates.items())
        if record_id not in latest
    ]
