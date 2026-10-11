"""Remove an erased conversation and its synthesis from the index."""

import sqlite3
from collections.abc import Iterable

from atrium.sql.load_sql import load_sql
from atrium.store.count_conversation_records import count_conversation_records
from atrium.store.write_conversation import write_conversation


def delete_erased_rows(connection: sqlite3.Connection, conversation_ids: Iterable[str]) -> int:
    """Delete the raw and ``synthesis/`` rows and revisions; return rows removed.

    Vectors follow by the ``vectors.record_id`` cascade, and the delete trigger
    moves the dense generation, so the resident service rebuilds its matrix.
    A conversation that keeps other fragments comes back from the next full
    ingest of the new generation; its synthesis does not, until re-synthesized.
    The caller owns the transaction.
    """
    removed = 0
    for conversation_id in conversation_ids:
        for indexed_id in (conversation_id, f"synthesis/{conversation_id}"):
            removed += count_conversation_records(connection, indexed_id)
            write_conversation(connection, indexed_id, [])
            connection.execute(load_sql("store/delete_revision"), (indexed_id,))
    return removed
