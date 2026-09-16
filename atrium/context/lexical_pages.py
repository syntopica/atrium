"""Page one MATCH expression into verified hits, under a budget when it is broad."""

import sqlite3
from typing import Any

from atrium.retrieve.bounded_rows import bounded_rows
from atrium.retrieve.fold import fold
from atrium.retrieve.hit import Hit
from atrium.retrieve.hits_from_rows import hits_from_rows

_PAGE = 200


def lexical_pages(  # noqa: PLR0913, PLR0917 -- one paging pass, fully parameterised
    connection: sqlite3.Connection,
    statement: str,
    parameters: tuple[Any, ...],
    expression: str,
    table: str,
    limit: int,
    *,
    verify: bool,
    verifiers: list[Any],
    seen: set[str],
    bounded: bool,
    exhausted: set[str],
    milliseconds: int,
) -> list[Hit]:
    """Return up to ``limit`` hits, skipping what ``seen`` already holds.

    ``bounded`` marks the broad pass. Its pages run under a wall-clock budget:
    an OR over a sentence's terms ranks most of a large corpus, and a caller
    that already has the narrow pass's hits must not wait minutes for more.
    """
    found: list[Hit] = []
    offset = 0
    page_size = max(limit, _PAGE)
    while True:
        arguments = (*parameters, expression, page_size, offset)
        rows = (
            bounded_rows(connection, statement, arguments, exhausted, milliseconds)
            if bounded
            else connection.execute(statement, arguments).fetchall()
        )
        if not rows:
            return found
        offset += page_size
        for row in rows:
            hit = hits_from_rows([row])[0]
            if hit.record_id in seen:
                continue
            if verify and not any(rx.search(fold(hit.text)) for rx in verifiers):
                continue
            seen.add(hit.record_id)
            found.append(
                Hit(
                    hit.record_id,
                    hit.text,
                    hit.score,
                    table,
                    hit.conversation_id,
                    hit.source_sha256,
                    hit.authored_at,
                    hit.provider,
                    hit.role,
                )
            )
            if len(found) == limit:
                return found
