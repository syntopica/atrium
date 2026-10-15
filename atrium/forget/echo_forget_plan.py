"""Plan one harness-echo forget pass: the events to append and the report."""

from pathlib import Path
from typing import Any

from atrium.forget.echo_candidates import echo_candidates
from atrium.forget.echo_forget_events import echo_forget_events
from atrium.forget.echo_forget_report import echo_forget_report
from atrium.forget.latest_events import latest_events
from atrium.forget.single_event_episodes import single_event_episodes
from atrium.synthesize.read_records import read_records


def echo_forget_plan(
    registry: Path, archive: Path, ledger: Path, today: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read the registry, the archive and the ledger; write nothing."""
    latest = latest_events(ledger)
    candidates = echo_candidates(archive, single_event_episodes(read_records(registry)))
    events = echo_forget_events(candidates, latest, today)
    return events, echo_forget_report(candidates, latest, events)
