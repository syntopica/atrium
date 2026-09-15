"""Check semantic coverage for the exact role and workspace being retrieved."""

import sqlite3

from atrium.context.context_scope import context_scope


def vector_presence(
    connection: sqlite3.Connection, *, curated: bool, workspace: str | None = None
) -> bool:
    """Report whether this pass can retrieve any eligible semantic evidence."""
    scope, parameters = context_scope(curated, workspace)
    return (
        connection.execute(
            "SELECT 1 FROM vectors v JOIN records r ON r.record_id = v.record_id WHERE 1 = 1"  # noqa: S608 -- fixed SQL fragments; data is bound
            + scope
            + " LIMIT 1",
            parameters,
        ).fetchone()
        is not None
    )
