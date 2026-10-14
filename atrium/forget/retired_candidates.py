"""Find the records that describe a retired thing as current."""

import sqlite3

from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement
from atrium.sql.load_sql import load_sql


def retired_candidates(
    connection: sqlite3.Connection, retirements: list[Retirement]
) -> dict[str, tuple[Retirement, str]]:
    """Return record id to the retirement it names and its role.

    Only history and episodes authored before the retirement date: later
    records are mostly "X is retired, use Y" and the migration itself, which is
    what keeps an agent from proposing X again. Curated notes are never
    candidates, because the brain is edited by its owner. ``LIKE`` narrows the
    scan; the whole-word match decides.
    """
    found: dict[str, tuple[Retirement, str]] = {}
    for retirement in retirements:
        for term in retirement.terms:
            rows = connection.execute(
                load_sql("forget/records_naming"),
                {"since": retirement.since, "pattern": f"%{term}%"},
            )
            for record_id, role, text in rows:
                if record_id not in found and names_retirement(text, retirement):
                    found[record_id] = (retirement, role)
    return found
