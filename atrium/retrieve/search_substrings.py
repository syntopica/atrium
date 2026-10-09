"""Substring retrieval — the fragment lane, deliberately separate from words."""

import sqlite3

from atrium.retrieve.hit import Hit
from atrium.retrieve.workspace_clause import workspace_clause
from atrium.sql.load_sql import load_sql

# FTS5's trigram tokenizer cannot match a fragment shorter than three characters.
MIN_FRAGMENT = 3


def search_substrings(
    connection: sqlite3.Connection,
    query: str,
    limit: int = 20,
    workspace: str | None = None,
) -> list[Hit]:
    """Return records containing ``query`` as a fragment, inside words included.

    This lane answers a different question from ``search_words`` and is exposed
    separately for that reason: searching `wal` here is *supposed* to return
    `wallpaper`. Merging the two is what made the previous system rank the exact
    `WAL` record seventh behind nine `wall...` matches.
    """
    fragment = query.strip()
    if len(fragment) < MIN_FRAGMENT:
        return []
    escaped = fragment.replace('"', '""')
    scope, scope_parameters = workspace_clause(workspace)
    rows = connection.execute(
        load_sql("retrieve/search_substrings").format(scope=scope),
        (f'"{escaped}"', *scope_parameters, limit),
    ).fetchall()
    return [
        Hit(
            record_id=row[0],
            text=row[1],
            score=float(row[2]),
            lane="substrings",
            conversation_id=row[3],
            source_sha256=row[4],
            authored_at=row[5],
            provider=row[6],
            role=row[7],
        )
        for row in rows
    ]
