"""Lexical retrieval narrowed by role and workspace before text reads."""

import sqlite3

from atrium.context.context_scope import context_scope
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_words import _fold, _hits, _match_expression, _verifiers


def lexical_hits(  # noqa: PLR0913 -- shared scope and lane contract
    connection: sqlite3.Connection,
    query: str,
    limit: int,
    lane: str,
    *,
    curated: bool,
    workspace: str | None = None,
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
        FROM {table} JOIN records r ON r.rowid = {table}.rowid
        WHERE {table} MATCH ? AND {table}.rowid IN (SELECT rowid FROM eligible)
        ORDER BY bm25({table}), r.record_id
        LIMIT ? OFFSET ?
    """  # noqa: S608 -- table is one of two hardcoded identifiers, data is bound
    verifiers, plain = _verifiers(query)
    hits = []
    offset = 0
    page_size = max(limit, 200)
    while True:
        rows = connection.execute(statement, (*parameters, match, page_size, offset)).fetchall()
        if not rows:
            break
        offset += page_size
        for row in rows:
            hit = _hits([row])[0]
            if (
                lane != "substring"
                and verifiers
                and not plain
                and not any(rx.search(_fold(hit.text)) for rx in verifiers)
            ):
                continue
            hits.append(
                Hit(
                    hit.record_id,
                    hit.text,
                    hit.score,
                    table,
                    hit.conversation_id,
                    hit.source_sha256,
                    hit.authored_at,
                    hit.provider,
                    hit.role,
                )
            )
            if len(hits) == limit:
                return hits
    return hits
