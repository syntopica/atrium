"""The most recent synthesized episodes for one workspace."""

import sqlite3

from atrium.retrieve.hit import Hit

_QUERY = """
SELECT record_id, text, conversation_id, source_sha256, authored_at, provider
FROM records
WHERE provider = 'synthesis' AND (workspace = ? OR workspace LIKE ? || '/%')
ORDER BY authored_at DESC, conversation_id, record_id
LIMIT ?
"""


def recent_episodes(connection: sqlite3.Connection, workspace: str, limit: int) -> list[Hit]:
    """Return this project's newest episodes, newest first.

    Session-start recall is not a search: there is no query yet. What a session
    needs is what the last sessions in this project concluded, so the selection
    is recency within the project, not relevance to a question.

    ``workspace`` is a prefix -- see ``project_workspace`` -- so a session run
    from a subdirectory of the project still recalls the project.

    Every episode of one conversation carries that conversation's timestamp, so
    ordering by time alone leaves ties that SQLite may break differently on
    each machine. Conversation and record id settle them, which keeps the
    injected snapshot reproducible from the same index.

    ``score`` is the row's position, negated, so that "higher is better" holds
    across everything that produces a ``Hit`` -- these are ordered by time, not
    ranked by relevance, and reporting a relevance score would be a lie.
    """
    rows = connection.execute(_QUERY, (workspace, workspace, limit)).fetchall()
    return [
        Hit(
            record_id=row[0],
            text=row[1],
            score=float(-position),
            lane="recent",
            conversation_id=row[2],
            source_sha256=row[3],
            authored_at=row[4],
            provider=row[5],
        )
        for position, row in enumerate(rows)
    ]
