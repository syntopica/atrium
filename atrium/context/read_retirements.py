"""Collect every retirement the curated notes in the index declare."""

import sqlite3

from atrium.context.parse_retirement import parse_retirement
from atrium.context.retirement import Retirement
from atrium.sql.load_sql import load_sql


def read_retirements(connection: sqlite3.Connection) -> list[Retirement]:
    """Return one retirement per declaring note, read from the indexed chunks.

    The declaration lives on the note, so the page that explains a retirement
    and the rule that applies it cannot drift apart, and the next
    ``ingest-notes`` picks up a new one with no other step.
    """
    found: dict[str, Retirement] = {}
    for note, text in connection.execute(load_sql("context/retirement_chunks")):
        if note not in found and (retirement := parse_retirement(text, note)):
            found[note] = retirement
    return list(found.values())
