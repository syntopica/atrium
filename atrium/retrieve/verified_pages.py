"""The word lane's two passes when every query term is punctuated."""

import re
import sqlite3
from typing import Any

from atrium.retrieve.bounded_rows import bounded_rows
from atrium.retrieve.fold import fold
from atrium.retrieve.hit import Hit
from atrium.retrieve.hits_from_rows import hits_from_rows

_PAGE = 200


def verified_pages(  # noqa: PLR0913, PLR0917 -- one pass pair, fully parameterised
    connection: sqlite3.Connection,
    statement: str,
    scope: tuple[Any, ...],
    conjunction: str,
    match: str,
    limit: int,
    verifiers: list[re.Pattern[str]],
    exhausted: set[str] | None,
) -> list[Hit]:
    """Page until enough hits pass the adjacency check, narrow question first.

    A fixed oversample cannot guarantee recall -- with 60 spaced `3 7 0` rows
    ranked above the one real `3.7.0`, any finite prefetch under 61 returns
    nothing (reproduced by review) -- so the OR pass keeps paging. That is also
    what made this branch unbounded: it kept the pre-2026-09-16 behaviour when
    the plain branch stopped ORing first, so a query of several punctuated terms
    still paid the full scan (raised by review, 2026-09-16).
    """
    verified: list[Hit] = []
    seen: set[str] = set()
    for expression, bounded in ((conjunction, False), (match, True)):
        if not expression:
            continue
        offset = 0
        while len(verified) < limit:
            arguments = (expression, *scope, _PAGE, offset)
            rows = (
                bounded_rows(connection, statement, arguments, exhausted)
                if bounded
                else connection.execute(statement, arguments).fetchall()
            )
            if not rows:
                break
            offset += _PAGE
            for hit in hits_from_rows(rows):
                if hit.record_id in seen or not any(rx.search(fold(hit.text)) for rx in verifiers):
                    continue
                seen.add(hit.record_id)
                verified.append(hit)
    return verified[:limit]
