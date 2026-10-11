"""Check the cached record total against the canonical records table."""

import sqlite3

from atrium.doctor.finding import Finding
from atrium.sql.load_sql import load_sql


def record_total_coherence(connection: sqlite3.Connection) -> Finding:
    """Report a mismatch as broken; an old read-only index may lack the cache."""
    try:
        cached = connection.execute(load_sql("store/read_record_total")).fetchone()
    except sqlite3.OperationalError as error:
        if "no such table: record_total" not in str(error):
            raise
        return Finding(
            check="record-total",
            severity="warn",
            code="record_total_unavailable",
            summary="record_total has not been installed by a writable open",
            detail={},
        )
    actual = int(connection.execute(load_sql("status/record_count")).fetchone()[0])
    counted = int(cached[0]) if cached is not None else None
    matches = counted == actual
    return Finding(
        check="record-total",
        severity="ok" if matches else "broken",
        code="record_total_consistent" if matches else "record_total_mismatch",
        summary=f"cached {counted} records; counted {actual}",
        detail={"cached": counted, "counted": actual},
    )
