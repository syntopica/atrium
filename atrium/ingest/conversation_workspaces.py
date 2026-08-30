"""The workspace each conversation was recorded in, read back from the index."""

import sqlite3


def conversation_workspaces(connection: sqlite3.Connection) -> dict[str, str]:
    """Map conversation id to workspace for every conversation that has one.

    Synthesis records are derived from a conversation but carry none of its
    provenance, and the registry record does not store the working directory
    either. The raw conversation is already indexed with it, so the index is
    the cheapest place to recover it -- no re-synthesis, no second archive read.

    The workspace is a property of the conversation, not of its events: the raw
    ingest reads it once and stamps every record with it, so one row per
    conversation answers this completely. ``min()`` rather than a bare
    ``GROUP BY`` projection, whose choice among differing values SQLite does
    not define -- if a conversation ever does carry two, this must answer the
    same thing on every machine rather than drift between them.
    """
    rows = connection.execute(
        """
        SELECT conversation_id, min(workspace) FROM records
        WHERE workspace IS NOT NULL AND provider != 'synthesis'
        GROUP BY conversation_id
        """
    )
    return dict(rows)
