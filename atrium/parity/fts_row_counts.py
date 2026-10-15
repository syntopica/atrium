"""How many rows each full-text lane holds a size for, against the records."""

import sqlite3

from atrium.sql.load_sql import load_sql


def fts_row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    """Return records and both lanes' docsize row counts.

    A lane emptied or never built has fewer docsize rows than records, which
    the ranked probe cannot see: it finds postings left behind, not postings
    missing. Postings missing for a row whose size is kept need the full
    check, `atrium --index <test> repair-index` without ``--apply``.
    """
    records, words, substrings = connection.execute(load_sql("parity/fts_row_counts")).fetchone()
    return {"records": records, "words": words, "substrings": substrings}
