"""Check one full-text index against the records it is built from."""

import sqlite3

from atrium.sql.load_sql import load_sql


def fts_integrity_error(connection: sqlite3.Connection, table: str) -> str | None:
    """Return the integrity failure of ``table``, or None when it is consistent.

    The check runs with ``rank = 1``, so FTS5 also compares the index with the
    ``records`` content table: a posting left behind for a deleted row is the
    failure that makes ranked queries raise "database disk image is malformed".
    """
    statement = {
        "words": load_sql("store/integrity_check_words"),
        "substrings": load_sql("store/integrity_check_substrings"),
    }[table]
    try:
        with connection:
            connection.execute(statement)
    except sqlite3.DatabaseError as error:
        return str(error)
    return None
