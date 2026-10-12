"""How long ago the pipeline that feeds this index last finished."""

import time
from pathlib import Path

from atrium.doctor.finding import Finding

# The LaunchAgent starts a refresh every hour and the stamp is written when it
# finishes, 15-25 minutes later, so between two healthy runs the stamp already
# ages past an hour: a one-hour threshold put a degraded warning on every prompt
# for about twenty minutes of each hour (2026-10-12). Two hours means a whole run
# was missed or ran far long; six means nothing is feeding the index. The
# sync orchestrator went eleven days dead on a stale lock and every run still
# printed "done"; the whole point of this check is that silence stops counting
# as health.
STALE_AFTER_SECONDS = 7200
BROKEN_AFTER_SECONDS = 21600
CODES = {"ok": "refresh_fresh", "warn": "refresh_stale", "broken": "refresh_dead"}


def refresh_health(stamp: Path, now: float | None = None) -> Finding:
    """Read the refresh stamp and say how old the index's newest input is."""
    moment = time.time() if now is None else now
    if not stamp.exists():
        return Finding(
            check="refresh",
            severity="broken",
            code="refresh_never_recorded",
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
        code=CODES[severity],
        summary=f"last refresh finished {int(age)}s ago",
        detail={"age_seconds": int(age), "stamp": str(stamp)},
    )
