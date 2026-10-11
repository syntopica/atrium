"""Remove an erased conversation and its synthesis from the index, leaving no copy."""

import sqlite3
from collections.abc import Iterable

from atrium.sql.load_sql import load_sql
from atrium.store.count_conversation_records import count_conversation_records
from atrium.store.write_conversation import write_conversation


def delete_erased_rows(connection: sqlite3.Connection, conversation_ids: Iterable[str]) -> int:
    """Delete the raw and ``synthesis/`` rows and revisions; return rows removed.

    A plain DELETE is not an erasure: SQLite leaves the row's bytes in the freed
    page, and an FTS5 delete only appends a tombstone while the old segment
    keeps the terms. ``secure_delete`` zeroes freed pages, and FTS5's
    ``secure-delete`` option removes the entries from the segments themselves;
    the option is persistent, so it is set back off before returning, leaving
    ordinary ingests at their usual cost. The caller owns the transaction and
    truncates the WAL after commit. Vectors follow by the ``vectors.record_id``
    cascade, and the delete trigger moves the dense generation.
    """
    connection.execute(load_sql("store/enable_secure_delete"))
    connection.execute(load_sql("store/set_words_secure_delete"), (1,))
    connection.execute(load_sql("store/set_substrings_secure_delete"), (1,))
    removed = 0
    for conversation_id in conversation_ids:
        for indexed_id in (conversation_id, f"synthesis/{conversation_id}"):
            removed += count_conversation_records(connection, indexed_id)
            write_conversation(connection, indexed_id, [])
            connection.execute(load_sql("store/delete_revision"), (indexed_id,))
    connection.execute(load_sql("store/set_words_secure_delete"), (0,))
    connection.execute(load_sql("store/set_substrings_secure_delete"), (0,))
    return removed
