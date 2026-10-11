"""Read the cached record total, including indexes predating the counter."""

import sqlite3

from atrium.sql.load_sql import load_sql


def read_record_total(connection: sqlite3.Connection) -> int:
    """Fall back to a full count only when a read-only index lacks the new table."""
    try:
        row = connection.execute(load_sql("store/read_record_total")).fetchone()
    except sqlite3.OperationalError as error:
        if "no such table: record_total" not in str(error):
            raise
        return int(connection.execute(load_sql("status/record_count")).fetchone()[0])
    if row is None:
        raise RuntimeError("record_total exists without its singleton row")
    return int(row[0])
