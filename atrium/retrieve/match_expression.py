"""The FTS5 MATCH expression for the word lane."""

from atrium.retrieve.query_terms import query_terms


def match_expression(query: str) -> str:
    """Join the query's terms with OR -- the lane's recall semantics."""
    return " OR ".join(query_terms(query))
