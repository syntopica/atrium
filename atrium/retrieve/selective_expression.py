"""The broad OR expression with its corpus-wide terms dropped."""

import sqlite3

from atrium.retrieve.query_terms import query_terms
from atrium.retrieve.rarest_terms import rarest_terms
from atrium.retrieve.term_frequency import term_frequency

# One percent of the corpus. FTS5 ranks every row a broad expression matches, so
# a term the corpus repeats drags that whole set through bm25 while contributing
# nothing that distinguishes one record from another: measured on 1,417,899
# records, "why does the stop hook fire on a status turn" did not finish the
# curated pass in 15s and returned nothing, and the same query without its terms
# above this share answered in 0.42s with 16 hits.
_SHARE = 0.01

# What a whole prompt sent as the query is matched on. Its rarest terms carry
# the match and every further one adds postings to rank: Elasticsearch's
# more_like_this makes the same cut at 25 by tf-idf.
_MAX_TERMS = 32


def selective_expression(connection: sqlite3.Connection, table: str, query: str, total: int) -> str:
    """Return ``query``'s terms OR-ed, minus the ones ``total`` makes worthless.

    Every term is kept when they are all common: a query made only of frequent
    words still has to be answered, and the caller's budget is what bounds it.
    Of what is left, only the ``_MAX_TERMS`` rarest indexed terms are asked.
    """
    frequencies = {term: term_frequency(connection, table, term) for term in query_terms(query)}
    ceiling = total * _SHARE
    selective = {term: count for term, count in frequencies.items() if count <= ceiling}
    return " OR ".join(rarest_terms(selective or frequencies, _MAX_TERMS))
