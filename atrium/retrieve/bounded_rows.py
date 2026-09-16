"""Run one statement under a wall-clock budget instead of letting it hang."""

import sqlite3
import time
from typing import Any

# Two seconds. The word lane's OR fallback is the only caller, and it is a
# fallback: what it can find in two seconds is worth having, and what it cannot
# is not worth a session waiting for. Measured on a 1,414,461-record index, one
# 200-row page of an OR over a sentence's terms costs 34-42s -- unbounded, that
# is what a hook or an interactive search pays before it can say anything.
_BUDGET_MILLISECONDS = 2000

# SQLite calls the handler every N virtual-machine instructions. Small enough
# that the deadline is honoured promptly, large enough that the check itself is
# not the cost.
_INSTRUCTIONS_PER_CHECK = 10_000


def bounded_rows(
    connection: sqlite3.Connection,
    statement: str,
    parameters: tuple[Any, ...],
    exhausted: set[str] | None = None,
    milliseconds: int = _BUDGET_MILLISECONDS,
) -> list[Any]:
    """Return the statement's rows, or an empty list when the budget ran out.

    Interruption loses the rows fetched so far, so this is all-or-nothing by
    construction rather than by choice. An empty result therefore has two
    meanings, and a caller that cannot tell them apart reports "nothing is
    known" for a query that merely ran out of time -- which is the failure this
    whole retrieval layer exists to avoid. So exhaustion is recorded in
    ``exhausted`` for the caller to surface, never swallowed.
    """
    deadline = time.monotonic() + milliseconds / 1000
    interrupted = False

    def expired() -> int:
        # The flag, not the exception message, is what says this deadline fired.
        # SQLite raises the same OperationalError for a locked database, a
        # missing table and a schema change, and catching all of them as "out of
        # time" turns a broken index into a silent empty answer (raised by
        # review, 2026-09-16).
        nonlocal interrupted
        if time.monotonic() <= deadline:
            return 0
        interrupted = True
        return 1

    connection.set_progress_handler(expired, _INSTRUCTIONS_PER_CHECK)
    try:
        return connection.execute(statement, parameters).fetchall()
    except sqlite3.OperationalError:
        if not interrupted:
            raise
        if exhausted is not None:
            exhausted.add("lexical_budget_exhausted")
        return []
    finally:
        connection.set_progress_handler(None, 0)
