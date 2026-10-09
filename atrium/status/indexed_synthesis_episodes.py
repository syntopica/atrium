"""The synthesis episode ids the index actually serves."""

import sqlite3

from atrium.sql.load_sql import load_sql


def indexed_synthesis_episodes(connection: sqlite3.Connection) -> set[str]:
    """Return every synthesis record's event id, one per served episode."""
    return {row[0] for row in connection.execute(load_sql("status/synthesis_event_ids"))}
