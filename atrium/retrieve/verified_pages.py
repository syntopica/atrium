"""The word lane's two passes when every query term is punctuated."""

import re
import sqlite3
from typing import Any

from atrium.retrieve.fold import fold
from atrium.retrieve.hit import Hit
from atrium.retrieve.ranked_hits import ranked_hits

_BUDGET_MILLISECONDS = 2000


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
    """Read in rank order until enough hits pass the adjacency check.

    A fixed oversample cannot guarantee recall -- with 60 spaced `3 7 0` rows
    ranked above the one real `3.7.0`, any finite prefetch under 61 returns
    nothing (reproduced by review) -- so the read keeps going until the limit is
    met or the budget is spent. Streaming is what makes that affordable: the
    previous shape re-ran the whole sorted statement per page.
    """
    verified: list[Hit] = []
    seen: set[str] = set()

    def accept(hit: Hit) -> bool:
        if hit.record_id in seen or not any(rx.search(fold(hit.text)) for rx in verifiers):
            return False
        seen.add(hit.record_id)
        return True

    for expression, reportable in ((conjunction, None), (match, exhausted)):
        if not expression or len(verified) >= limit:
            continue
        verified += ranked_hits(
            connection,
            statement,
            (expression, *scope),
            limit - len(verified),
            _BUDGET_MILLISECONDS,
            accept,
            reportable,
        )
    return verified[:limit]
