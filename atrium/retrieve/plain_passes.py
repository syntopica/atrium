"""The word lane's two passes when at least one query term is a plain word."""

import sqlite3
from typing import Any

from atrium.retrieve.bounded_rows import bounded_rows
from atrium.retrieve.hit import Hit
from atrium.retrieve.hits_from_rows import hits_from_rows


def plain_passes(  # noqa: PLR0913, PLR0917 -- one pass pair, fully parameterised
    connection: sqlite3.Connection,
    statement: str,
    scope: tuple[Any, ...],
    conjunction: str,
    match: str,
    limit: int,
    exhausted: set[str] | None,
) -> list[Hit]:
    """Answer from the intersection first, then widen under a budget.

    See `conjunctive_expression` for the measurement: ORing a sentence's terms
    ranks most of a large corpus, while the same terms intersected do not.
    """
    found: list[Hit] = []
    if conjunction:
        found = hits_from_rows(
            connection.execute(statement, (conjunction, *scope, limit, 0)).fetchall()
        )
    if len(found) >= limit:
        return found[:limit]
    seen = {hit.record_id for hit in found}
    rows = bounded_rows(connection, statement, (match, *scope, limit, 0), exhausted)
    found.extend(hit for hit in hits_from_rows(rows) if hit.record_id not in seen)
    return found[:limit]
