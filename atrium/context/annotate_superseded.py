"""Mark each evidence item a later statement replaced."""

import sqlite3
from typing import Any

from atrium.context.read_supersessions import read_supersessions


def annotate_superseded(connection: sqlite3.Connection, response: dict[str, Any]) -> None:
    """Add ``superseded_by`` and ``superseded_at`` to every superseded evidence item.

    Reads the marks for the selected evidence only, so the reader of an answer
    always learns that an item was replaced, and by which record.
    """
    marks = read_supersessions(connection, [item["record_id"] for item in response["evidence"]])
    for item in response["evidence"]:
        mark = marks.get(item["record_id"])
        if mark is not None:
            item["superseded_by"] = mark.superseded_by
            item["superseded_at"] = mark.at
