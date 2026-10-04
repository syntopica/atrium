"""The `synthesis passes` document: recent passes, the last one, and progress."""

from pathlib import Path
from typing import Any

from atrium.ledger.log_tail_lines import log_tail_lines
from atrium.ledger.parse_pass_log import parse_pass_log
from atrium.ledger.pass_progress import pass_progress
from atrium.status.iso_utc import iso_utc
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION

# The scheduled wrapper's two logs, beside the records they describe: one
# line per pass start and end, and the running pass's own output.
TICK_LOG = "synthesis.log"
OUTPUT_LOG = "synthesis-pass.log"


def synthesis_passes(registry: Path, now: float, limit: int) -> dict[str, Any]:
    """Describe the newest ``limit`` passes, newest first.

    ``synthesis.json`` is published only by a pass that ends by itself, so a
    pass the time box kills leaves it describing an older pass. The tick log
    records every end, including the exit status of a killed one.
    """
    passes = parse_pass_log(log_tail_lines(registry / TICK_LOG))
    last = passes[-1] if passes else None
    streak = 0
    for entry in reversed(passes):
        if entry["state"] == "running":
            continue
        if entry["state"] == "ok":
            break
        streak += 1
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "writtenAt": iso_utc(now),
        "lastPass": last,
        "unsuccessfulStreak": streak,
        "progress": pass_progress(registry / OUTPUT_LOG)
        if last is not None and last["state"] == "running"
        else None,
        "passes": list(reversed(passes[-limit:])),
    }
