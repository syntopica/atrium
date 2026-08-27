"""Remove a provider's conversations that the new canonical source no longer has."""

import sqlite3
from collections.abc import Iterable


def delete_absent_conversations(
    connection: sqlite3.Connection, provider: str, seen_conversation_ids: Iterable[str]
) -> int:
    """Delete every record of ``provider`` whose conversation was not seen.

    Per-conversation replacement only reconciles conversations that still exist
    in the source; a conversation deleted or redacted away upstream never
    appears in the new input, so nothing would ever remove it. The archive is
    canonical: after ingesting a source's archive, the index must hold exactly
    that archive's conversations for that provider -- and vectors follow via
    the cascade.

    The caller owns the transaction, and must only call this for a source it
    ingested completely (a partial ingest would sweep away the rest).
    """
    connection.execute("CREATE TEMP TABLE IF NOT EXISTS seen_conversations (id TEXT PRIMARY KEY)")
    connection.execute("DELETE FROM seen_conversations")
    connection.executemany(
        "INSERT OR IGNORE INTO seen_conversations (id) VALUES (?)",
        ((conversation_id,) for conversation_id in seen_conversation_ids),
    )
    cursor = connection.execute(
        "DELETE FROM records WHERE provider = ? "
        "AND conversation_id NOT IN (SELECT id FROM seen_conversations)",
        (provider,),
    )
    connection.execute("DELETE FROM seen_conversations")
    return cursor.rowcount
