"""Rebuild one full-text index from the records it indexes."""

import sqlite3

from atrium.sql.load_sql import load_sql


def rebuild_fts(connection: sqlite3.Connection, table: str) -> None:
    """Drop every posting of ``table`` and index each record again, in one transaction."""
    statement = {
        "words": load_sql("store/rebuild_words"),
        "substrings": load_sql("store/rebuild_substrings"),
    }[table]
    with connection:
        connection.execute(statement)
