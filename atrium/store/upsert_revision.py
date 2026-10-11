"""Record what one conversation reconciled to."""

import sqlite3

from atrium.sql.load_sql import load_sql
from atrium.store.revision import Revision


def upsert_revision(
    connection: sqlite3.Connection, conversation_id: str, provider: str, revision: Revision
) -> None:
    """Write ``revision``; the caller owns the transaction that wrote the rows it describes."""
    connection.execute(
        load_sql("store/upsert_revision"),
        (
            conversation_id,
            provider,
            revision.rows_sha256,
            revision.canonical_workspace,
            revision.disposition,
        ),
    )
