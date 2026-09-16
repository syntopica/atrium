"""The AND expression the word lane tries before the OR one, and why it exists."""

from atrium.retrieve.query_terms import query_terms

_SMALLEST_CONJUNCTION = 2


def conjunctive_expression(query: str) -> str:
    """Return ``query``'s terms joined by AND, or "" when there is nothing to narrow.

    The word lane ORs its terms, which is the right recall semantics and a
    pathological scan: FTS5 ranks the whole match set, so one common term drags
    the entire corpus through `bm25`. Measured on a 1,414,461-record index, the
    sentence "why does the stop hook fire on a status turn" did not finish in
    120s -- `the` alone is in 483,947 records -- while the same nine terms joined
    by AND answered in 0.36s, because the intersection is small.

    So the lane asks the narrow question first and keeps the broad one as the
    fallback. A single-term query has nothing to intersect and returns "", which
    sends it straight down the OR path it would have taken anyway.
    """
    terms = query_terms(query)
    if len(terms) < _SMALLEST_CONJUNCTION:
        return ""
    return " AND ".join(terms)
