"""How many indexed records hold one term -- the cost signal for a broad match."""

import sqlite3

from atrium.sql.load_sql import load_sql


def term_frequency(connection: sqlite3.Connection, table: str, term: str) -> int:
    """Return the number of records ``term`` matches in ``table``.

    FTS5 answers this from the term's doclist without reading a record, so it is
    cheap enough to ask before building an expression: measured at 19ms for the
    corpus's most common word (`the`, 485,117 records of 1,417,899) and 4ms for
    an ordinary one.
    """
    # The caller passes one of two hardcoded identifiers; the term is bound.
    statement = load_sql("retrieve/term_frequency").format(table=table)
    return int(connection.execute(statement, (term,)).fetchone()[0])
