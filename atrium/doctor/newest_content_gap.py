"""How far behind the present the index's newest content sits."""

import sqlite3
import time
from datetime import datetime

from atrium.doctor.finding import Finding


def newest_content_gap(connection: sqlite3.Connection, now: float | None = None) -> Finding:
    """Report the gap between the newest indexed record and now.

    The gap alone is not a verdict: a quiet weekend grows it while capture is
    perfectly healthy, so this finding never escalates past ``warn``. It exists
    to be read next to the archive and refresh checks -- a gap of days beside a
    fresh archive means ingest stopped reading what capture writes. The index
    sat frozen from 2026-08-27 while answering every query as if current, and
    nothing printed this number.
    """
    moment = time.time() if now is None else now
    newest = connection.execute(
        "SELECT max(authored_at) FROM records WHERE authored_at IS NOT NULL"
    ).fetchone()[0]
    if not newest:
        return Finding(
            check="content",
            severity="warn",
            summary="no record carries an authored timestamp",
            detail={},
        )
    authored = datetime.fromisoformat(newest.replace("Z", "+00:00"))
    gap = int(moment - authored.timestamp())
    return Finding(
        check="content",
        severity="ok",
        summary=f"newest indexed content authored {gap}s ago",
        detail={"newest_authored_at": newest, "gap_seconds": gap},
    )
