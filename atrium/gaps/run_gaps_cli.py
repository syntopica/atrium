"""The `atrium gaps` command: what sessions asked that the memory could not answer."""

import json
from datetime import UTC, datetime
from pathlib import Path

from atrium.gaps.gap_report import gap_report
from atrium.gaps.read_query_events import read_query_events


def run_gaps_cli(state: Path, days: int, top: int) -> int:
    """Print the report as JSON for the last ``days`` days of the query log."""
    events = read_query_events(state / "synthesis" / "queries", days, datetime.now(UTC).date())
    print(json.dumps({"days": days, **gap_report(events, top)}, ensure_ascii=False, indent=1))
    return 0
