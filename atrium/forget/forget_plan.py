"""Plan one forget or restore pass: the events to append and the report."""

from pathlib import Path
from typing import Any

from atrium.context.read_retirements import read_retirements
from atrium.forget.forget_report import forget_report
from atrium.forget.latest_events import latest_events
from atrium.forget.restore_events import restore_events
from atrium.forget.retired_candidates import retired_candidates
from atrium.forget.retired_forget_events import retired_forget_events
from atrium.store.open_store import open_store


def forget_plan(
    index: Path, ledger: Path, restore: str | None, today: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read the ledger and, for a forget pass, the index; write nothing."""
    latest = latest_events(ledger)
    if restore is not None:
        events = restore_events(restore, latest, today)
        return events, {"restore": restore, "restored": len(events), "applied": False}
    connection = open_store(index, read_only=True)
    try:
        candidates = retired_candidates(connection, read_retirements(connection))
    finally:
        connection.close()
    events = retired_forget_events(candidates, latest, today)
    return events, forget_report(candidates, latest, events)
