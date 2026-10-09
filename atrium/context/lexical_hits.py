"""Lexical retrieval narrowed by role and workspace before text reads."""

import dataclasses
import sqlite3

from atrium.context.context_scope import context_scope
from atrium.retrieve.conjunctive_expression import conjunctive_expression
from atrium.retrieve.fold import fold
from atrium.retrieve.hit import Hit
from atrium.retrieve.match_expression import match_expression
from atrium.retrieve.ranked_hits import ranked_hits
from atrium.retrieve.selective_expression import selective_expression
from atrium.retrieve.word_verifiers import word_verifiers
from atrium.sql.load_sql import load_sql

# Both passes stream in rank order now, so these bound a pathology rather than
# the ordinary case: measured on 1,417,899 records, the narrow pass costs 0.03s
# and the broad one 0.15-0.48s against either scope. What they still catch is a
# match set large enough that even walking it in rank order takes seconds.
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
        match = match_expression(query)
    if not match:
        return []
    scope, parameters = context_scope(curated, workspace)
    # The table is one of two hardcoded identifiers and the scope is a fixed
    # fragment; every value is bound.
    statement = load_sql("context/lexical_hits").format(scope=scope, table=table)
    verifiers, plain = word_verifiers(query)
    verify = lane != "substring" and bool(verifiers) and not plain
    seen: set[str] = set()

    def accept(hit: Hit) -> bool:
        if hit.record_id in seen:
            return False
        if verify and not any(pattern.search(fold(hit.text)) for pattern in verifiers):
            return False
        seen.add(hit.record_id)
        return True

    # The narrow pass first. A context query is usually a sentence, and ORing a
    # sentence's terms matches most of a large index, so the intersection is
    # both the cheaper question and the one that usually answers.
    found: list[Hit] = []
    conjunction = "" if lane == "substring" else conjunctive_expression(query)
    passes = ((conjunction, _NARROW_BUDGET, False), (match, _BROAD_BUDGET, True))
    for candidate, milliseconds, broad in passes:
        if not candidate or len(found) >= limit:
            continue
        expression = candidate
        if broad and lane != "substring":
            # Only the broad pass needs this, and asking costs a query per term:
            # a narrow pass that answered must not pay for it (raised by review,
            # 2026-09-16).
            total = int(connection.execute(load_sql("status/record_count")).fetchone()[0])
            expression = selective_expression(connection, table, query, total)
            if not expression:
                continue
        found += ranked_hits(
            connection,
            statement,
            (*parameters, expression),
            limit - len(found),
            milliseconds,
            accept,
            exhausted,
        )
    return [dataclasses.replace(hit, lane=table) for hit in found]
