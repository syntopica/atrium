"""Substring retrieval — the fragment lane, deliberately separate from words."""

import sqlite3

from atrium.retrieve.hit import Hit
from atrium.retrieve.workspace_scope import workspace_clause

_QUERY = """
SELECT r.record_id, r.text, -bm25(substrings) AS score, r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM substrings
JOIN records r ON r.rowid = substrings.rowid
WHERE substrings MATCH ?{scope}
ORDER BY bm25(substrings)
LIMIT ?
"""

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
        _QUERY.format(scope=scope), (f'"{escaped}"', *scope_parameters, limit)
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
