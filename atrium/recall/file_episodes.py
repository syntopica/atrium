"""The synthesized episodes of one project that name one file."""

import sqlite3

from atrium.retrieve.hit import Hit
from atrium.sql.load_sql import load_sql


def file_episodes(
    connection: sqlite3.Connection, workspace: str, phrase: str, limit: int
) -> list[Hit]:
    """Return them newest first; ``score`` is the negated position, as in recall.

    Recency rather than relevance: the question is what this project last
    concluded about the file about to change, and the newest word on it is
    the one most likely to still hold.
    """
    rows = connection.execute(
        load_sql("recall/file_episodes"), (phrase, workspace, workspace, workspace, limit)
    ).fetchall()
    return [
        Hit(row[0], row[1], float(-position), "file", row[2], row[3], row[4], row[5], row[6])
        for position, row in enumerate(rows)
    ]
