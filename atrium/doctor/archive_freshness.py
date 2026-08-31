"""Whether the canonical archive itself is still being written."""

import time
from pathlib import Path

from atrium.doctor.finding import Finding

# Capture writes the archive on every refresh, so its mtime is the age of the
# newest thing the index could possibly know. An archive older than a day means
# capture has stopped, and every answer from here on describes a world that
# stopped moving -- without saying so.
STALE_AFTER_SECONDS = 7200
BROKEN_AFTER_SECONDS = 86400


def archive_freshness(archive: Path, now: float | None = None) -> Finding:
    """Report how long ago the canonical archive was last written."""
    moment = time.time() if now is None else now
    if not archive.exists():
        return Finding(
            check="archive",
            severity="broken",
            summary="the canonical archive does not exist",
            detail={"archive": str(archive)},
        )
    age = moment - archive.stat().st_mtime
    severity = (
        "broken" if age > BROKEN_AFTER_SECONDS else "warn" if age > STALE_AFTER_SECONDS else "ok"
    )
    return Finding(
        check="archive",
        severity=severity,
        summary=f"archive last written {int(age)}s ago",
        detail={"age_seconds": int(age), "bytes": archive.stat().st_size},
    )
