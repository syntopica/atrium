"""Collect every retirement the curated notes in the index declare."""

import sqlite3

from atrium.context.parse_retirement import parse_retirement
from atrium.context.retirement import Retirement
from atrium.sql.load_sql import load_sql


def read_retirements(connection: sqlite3.Connection) -> list[Retirement]:
    """Return every retirement declared in the indexed note chunks.

    A note may declare several, one per section: ``brain/retired.md`` lists
    them all, so the page about a retired tool can be deleted without losing
    the declaration. The next ``ingest-notes`` picks up a new one with no
    other step.
    """
    found: dict[tuple[str, tuple[str, ...]], Retirement] = {}
    for note, text in connection.execute(load_sql("context/retirement_chunks")):
        retirement = parse_retirement(text, note)
        if retirement is not None:
            found.setdefault((note, retirement.terms), retirement)
    return list(found.values())
