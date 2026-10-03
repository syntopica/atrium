"""The synthesis episode ids the index actually serves."""

import sqlite3


def indexed_synthesis_episodes(connection: sqlite3.Connection) -> set[str]:
    """Return every synthesis record's event id, one per served episode."""
    return {
        row[0]
        for row in connection.execute("SELECT event_id FROM records WHERE provider = 'synthesis'")
    }
