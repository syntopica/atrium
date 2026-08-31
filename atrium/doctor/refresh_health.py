"""How long ago the pipeline that feeds this index last finished."""

import time
from pathlib import Path

from atrium.doctor.finding import Finding

# The refresh runs on a 15-minute floor and a LaunchAgent, so an hour without
# one is already unusual and six hours means nothing is feeding the index. The
# sync orchestrator went eleven days dead on a stale lock and every run still
# printed "done"; the whole point of this check is that silence stops counting
# as health.
STALE_AFTER_SECONDS = 3600
BROKEN_AFTER_SECONDS = 21600


def refresh_health(stamp: Path, now: float | None = None) -> Finding:
    """Read the refresh stamp and say how old the index's newest input is."""
    moment = time.time() if now is None else now
    if not stamp.exists():
        return Finding(
            check="refresh",
            severity="broken",
            summary="no refresh has ever recorded a completion",
            detail={"stamp": str(stamp)},
        )
    age = moment - float(stamp.read_text().strip())
    severity = (
        "broken" if age > BROKEN_AFTER_SECONDS else "warn" if age > STALE_AFTER_SECONDS else "ok"
    )
    return Finding(
        check="refresh",
        severity=severity,
        summary=f"last refresh finished {int(age)}s ago",
        detail={"age_seconds": int(age), "stamp": str(stamp)},
    )
