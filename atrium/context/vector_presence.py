"""Check semantic coverage for the exact role and workspace being retrieved."""

import sqlite3

from atrium.context.context_scope import context_scope
from atrium.sql.load_sql import load_sql


def vector_presence(
    connection: sqlite3.Connection, *, curated: bool, workspace: str | None = None
) -> bool:
    """Report whether this pass can retrieve any eligible semantic evidence."""
    scope, parameters = context_scope(curated, workspace)
    return (
        connection.execute(
            load_sql("context/vector_presence").format(scope=scope), parameters
        ).fetchone()
        is not None
    )
