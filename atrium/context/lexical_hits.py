"""Lexical retrieval narrowed by role and workspace before text reads."""

import sqlite3

from atrium.context.context_scope import context_scope
from atrium.context.lexical_pages import lexical_pages
from atrium.retrieve.conjunctive_expression import conjunctive_expression
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_words import _match_expression, _verifiers
from atrium.retrieve.selective_expression import selective_expression

# The narrow pass gets the larger share because it is the one that answers.
# Measured on 1,417,899 records after the scope became a join: the same
# `"stop" AND "hook" AND "json"` costs 0.31s against the curated scope and 0.00s
# against a workspace, so 3s is headroom rather than a working budget. The broad
# pass keeps the smaller share because it usually spends all of it.
_NARROW_BUDGET = 3000
_BROAD_BUDGET = 1200


def lexical_hits(  # noqa: PLR0913 -- shared scope and lane contract
    connection: sqlite3.Connection,
    query: str,
    limit: int,
    lane: str,
    *,
    curated: bool,
    workspace: str | None = None,
    exhausted: set[str] | None = None,
) -> list[Hit]:
    """Use existing lexical token rules with a role filter inside the query."""
    table = "substrings" if lane == "substring" else "words"
    if lane == "substring":
        if len(query.strip()) < 3:  # noqa: PLR2004 -- FTS trigram minimum
            return []
        match = '"' + query.strip().replace('"', '""') + '"'
    else:
        match = _match_expression(query)
    if not match:
        return []
    scope, parameters = context_scope(curated, workspace)
    statement = f"""
        WITH eligible AS MATERIALIZED (
            SELECT r.rowid FROM records r WHERE 1 = 1{scope}
        )
        SELECT r.record_id, r.text, -bm25({table}), r.conversation_id,
               r.source_sha256, r.authored_at, r.provider, r.role
        FROM {table}
        JOIN eligible e ON e.rowid = {table}.rowid
        JOIN records r ON r.rowid = {table}.rowid
        WHERE {table} MATCH ?
        ORDER BY bm25({table}), r.record_id
        LIMIT ? OFFSET ?
    """  # noqa: S608 -- table is one of two hardcoded identifiers, data is bound
    verifiers, plain = _verifiers(query)
    verify = lane != "substring" and bool(verifiers) and not plain
    seen: set[str] = set()
    # The narrow pass first. A context query is usually a sentence, and ORing a
    # sentence's terms ranks most of a large index: measured at over 120s where
    # the same nine terms joined by AND took 0.36s (`conjunctive_expression`).
    # The broad pass then runs budgeted, so the lane answers in seconds with
    # what it has rather than in minutes with everything.
    found: list[Hit] = []
    conjunction = "" if lane == "substring" else conjunctive_expression(query)
    if lane != "substring":
        total = int(connection.execute("SELECT count(*) FROM records").fetchone()[0])
        match = selective_expression(connection, table, query, total)
    # Both passes are budgeted here, unlike the unscoped `search_words` path:
    # the broad one still ranks a large match set even with its common terms
    # dropped, and the narrow one is only cheap while the scope reaches the FTS
    # table as a join (see the statement above).
    for expression, milliseconds in ((conjunction, _NARROW_BUDGET), (match, _BROAD_BUDGET)):
        # The broad pass only runs when the narrow one found nothing. It costs
        # its whole budget nearly every time -- an OR still ranks a large match
        # set -- and measured across the curated scope it added no hit the
        # narrow pass had missed. It stays for the query whose terms never
        # co-occur, which is the only case it ever answered.
        if not expression or found:
            continue
        found += lexical_pages(
            connection,
            statement,
            parameters,
            expression,
            table,
            limit,
            verify=verify,
            verifiers=verifiers,
            seen=seen,
            exhausted=exhausted if exhausted is not None else set(),
            bounded=True,
            milliseconds=milliseconds,
        )
    return found
