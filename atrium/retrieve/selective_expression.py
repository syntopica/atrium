"""The broad OR expression with its corpus-wide terms dropped."""

import sqlite3

from atrium.retrieve.query_terms import query_terms
from atrium.retrieve.term_frequency import term_frequency

# One percent of the corpus. FTS5 ranks every row a broad expression matches, so
# a term the corpus repeats drags that whole set through bm25 while contributing
# nothing that distinguishes one record from another: measured on 1,417,899
# records, "why does the stop hook fire on a status turn" did not finish the
# curated pass in 15s and returned nothing, and the same query without its terms
# above this share answered in 0.42s with 16 hits.
_SHARE = 0.01


def selective_expression(connection: sqlite3.Connection, table: str, query: str, total: int) -> str:
    """Return ``query``'s terms OR-ed, minus the ones ``total`` makes worthless.

    Every term is kept when they are all common: a query made only of frequent
    words still has to be answered, and the caller's budget is what bounds it.
    """
    terms = query_terms(query)
    if not terms:
        return ""
    ceiling = total * _SHARE
    selective = [term for term in terms if term_frequency(connection, table, term) <= ceiling]
    return " OR ".join(selective or terms)
