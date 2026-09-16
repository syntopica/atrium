"""Read a match in FTS rank order and stop at the limit, instead of sorting it all."""

import sqlite3
import time
from collections.abc import Callable
from typing import Any

from atrium.retrieve.hit import Hit
from atrium.retrieve.hits_from_rows import hits_from_rows

# The same cadence `bounded_rows` used: often enough that a deadline is honoured
# promptly, rarely enough that the check is not the cost.
_INSTRUCTIONS_PER_CHECK = 10_000


def ranked_hits(  # noqa: PLR0913, PLR0917 -- one streaming read, fully parameterised
    connection: sqlite3.Connection,
    statement: str,
    parameters: tuple[Any, ...],
    limit: int,
    milliseconds: int,
    accept: Callable[[Hit], bool],
    exhausted: set[str] | None = None,
) -> list[Hit]:
    """Return the best ``limit`` hits ``accept`` keeps, in score then id order.

    ``statement`` must end in `ORDER BY <table>.rank` and carry no LIMIT: that
    is the FTS5 rank optimisation, which walks the match in descending score
    instead of ranking it into a temporary b-tree. Measured on 1,417,899
    records, `"stop" OR "hook" OR "json"` unscoped took 17.6s to sort and 0.18s
    to stream, and a five-term OR that never finished in 30s streams its top 20
    in 0.57s.

    Reading stops one row after the limit is reached, plus every row that ties
    the cutoff score, so the result is the same set the sorted statement
    returned rather than whichever tie the scan met first.

    A deadline here loses nothing. `bounded_rows` had to interrupt a statement
    that sorts before it returns a single row, so an expired budget meant an
    empty answer; a streaming read keeps every hit it has already taken, and
    reports the budget as spent on top of them (raised by review, 2026-09-16).
    """
    deadline = time.monotonic() + milliseconds / 1000
    interrupted = False

    def expired() -> int:
        nonlocal interrupted
        if time.monotonic() <= deadline:
            return 0
        interrupted = True
        return 1

    found: list[Hit] = []
    cutoff: float | None = None
    connection.set_progress_handler(expired, _INSTRUCTIONS_PER_CHECK)
    cursor = connection.cursor()
    try:
        for row in cursor.execute(statement, parameters):
            # The deadline is checked here as well as inside SQLite. The progress
            # handler only fires while the VM steps, so a read whose cost is on
            # this side -- a verifier regex, a long row -- would run past the
            # budget unnoticed (a rewritten regression caught this).
            if time.monotonic() > deadline:
                interrupted = True
                break
            hit = hits_from_rows([row])[0]
            if cutoff is not None and hit.score < cutoff:
                break
            if accept(hit):
                found.append(hit)
                if len(found) == limit:
                    cutoff = hit.score
        if interrupted and exhausted is not None:
            exhausted.add("lexical_budget_exhausted")
    except sqlite3.OperationalError:
        # Only this deadline's interrupt is swallowed. A locked database, a
        # missing table and a schema change raise the same exception, and
        # reading those as "out of time" turns a broken index into a confident
        # empty answer.
        if not interrupted:
            raise
        if exhausted is not None:
            exhausted.add("lexical_budget_exhausted")
    finally:
        cursor.close()
        connection.set_progress_handler(None, 0)
    found.sort(key=lambda hit: (-hit.score, hit.record_id))
    return found[:limit]
