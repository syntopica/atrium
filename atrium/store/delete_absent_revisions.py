"""Drop the revisions of a provider's conversations the source no longer has."""

import sqlite3
from collections.abc import Iterable

from atrium.sql.load_sql import load_sql


def delete_absent_revisions(
    connection: sqlite3.Connection, provider: str, seen_conversation_ids: Iterable[str]
) -> int:
    """Delete every revision of ``provider`` whose conversation was not seen.

    The companion of ``delete_absent_conversations``, with the same contract: only
    after a complete pass over the provider's source, inside the caller's
    transaction. A revision left behind for a deleted conversation would let a
    conversation that reappears unchanged skip its rewrite and stay missing.
    """
    connection.execute(load_sql("store/create_seen_conversations"))
    connection.execute(load_sql("store/clear_seen_conversations"))
    connection.executemany(
        load_sql("store/insert_seen_conversation"),
        ((conversation_id,) for conversation_id in seen_conversation_ids),
    )
    cursor = connection.execute(load_sql("store/delete_unseen_revisions"), (provider,))
    connection.execute(load_sql("store/clear_seen_conversations"))
    return cursor.rowcount
