"""How many index records one conversation holds."""

import sqlite3

from atrium.sql.load_sql import load_sql


def count_conversation_records(connection: sqlite3.Connection, conversation_id: str) -> int:
    """Return the number of rows stored under ``conversation_id``."""
    row = connection.execute(load_sql("store/count_conversation_records"), (conversation_id,))
    return int(row.fetchone()[0])
