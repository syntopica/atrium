"""The word lane's two passes when at least one query term is a plain word."""

import sqlite3
from typing import Any

from atrium.retrieve.hit import Hit
from atrium.retrieve.ranked_hits import ranked_hits

# The narrow pass is an intersection and answers in milliseconds; the broad one
# streams in rank order, which is what took a sentence's OR from over 120s to
# under a second. The budget is here for the match set large enough that even
# streaming it takes seconds.
_BUDGET_MILLISECONDS = 2000


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
    matches most of a large corpus, while the same terms intersected do not.
    """
    found: list[Hit] = []
    seen: set[str] = set()

    def accept(hit: Hit) -> bool:
        if hit.record_id in seen:
            return False
        seen.add(hit.record_id)
        return True

    if conjunction:
        found = ranked_hits(
            connection, statement, (conjunction, *scope), limit, _BUDGET_MILLISECONDS, accept
        )
    if len(found) >= limit:
        return found[:limit]
    found += ranked_hits(
        connection,
        statement,
        (match, *scope),
        limit - len(found),
        _BUDGET_MILLISECONDS,
        accept,
        exhausted,
    )
    return found[:limit]
