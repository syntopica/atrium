"""The most recent synthesized episodes for one workspace."""

import sqlite3

from atrium.retrieve.hit import Hit
from atrium.sql.load_sql import load_sql


def recent_episodes(connection: sqlite3.Connection, workspace: str, limit: int) -> list[Hit]:
    """Return this project's newest episodes, newest first.

    Session-start recall is not a search: there is no query yet. What a session
    needs is what the last sessions in this project concluded, so the selection
    is recency within the project, not relevance to a question.

    ``workspace`` is a prefix -- see ``project_workspace`` -- so a session run
    from a subdirectory of the project still recalls the project. The prefix is
    compared with ``substr`` rather than ``LIKE``: a path is not a pattern, and
    2,585 workspaces in this index contain ``_``, which ``LIKE`` reads as "any
    character" and which would quietly pull a neighbouring project's memory in.

    Every episode of one conversation carries that conversation's timestamp, so
    ordering by time alone leaves ties that SQLite may break differently on
    each machine. Conversation and record id settle them, which keeps the
    injected snapshot reproducible from the same index.

    ``score`` is the row's position, negated, so that "higher is better" holds
    across everything that produces a ``Hit`` -- these are ordered by time, not
    ranked by relevance, and reporting a relevance score would be a lie.
    """
    rows = connection.execute(
        load_sql("recall/recent_episodes"), (workspace,) * 5 + (limit,)
    ).fetchall()
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
            role=row[6],
        )
        for position, row in enumerate(rows)
    ]
