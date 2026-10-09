"""Word-level lexical retrieval -- the exact-recall lane."""

import sqlite3

from atrium.retrieve.conjunctive_expression import conjunctive_expression
from atrium.retrieve.hit import Hit
from atrium.retrieve.match_expression import match_expression
from atrium.retrieve.plain_passes import plain_passes
from atrium.retrieve.verified_pages import verified_pages
from atrium.retrieve.word_verifiers import word_verifiers
from atrium.retrieve.workspace_clause import workspace_clause
from atrium.sql.load_sql import load_sql


def search_words(
    connection: sqlite3.Connection,
    query: str,
    limit: int = 20,
    workspace: str | None = None,
    exhausted: set[str] | None = None,
) -> list[Hit]:
    """Return records matching ``query`` on word boundaries, optionally scoped."""
    match = match_expression(query)
    if not match:
        return []
    scope, scope_parameters = workspace_clause(workspace)
    statement = load_sql("retrieve/search_words").format(scope=scope)
    verifiers, has_plain_term = word_verifiers(query)
    conjunction = conjunctive_expression(query)
    if has_plain_term or not verifiers:
        return plain_passes(
            connection, statement, scope_parameters, conjunction, match, limit, exhausted
        )
    return verified_pages(
        connection, statement, scope_parameters, conjunction, match, limit, verifiers, exhausted
    )
