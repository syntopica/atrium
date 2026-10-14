"""The record ids an ingest must turn away."""

from pathlib import Path

from atrium.forget.latest_events import latest_events


def forgotten_ids(ledger: Path) -> frozenset[str]:
    """Return every record whose latest ledger event is ``forget``."""
    return frozenset(
        record_id
        for record_id, event in latest_events(ledger).items()
        if event["event"] == "forget"
    )
