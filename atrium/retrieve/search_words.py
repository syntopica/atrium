"""Word-level lexical retrieval -- the exact-recall lane."""

import sqlite3

from atrium.retrieve.conjunctive_expression import conjunctive_expression
from atrium.retrieve.hit import Hit
from atrium.retrieve.match_expression import match_expression
from atrium.retrieve.plain_passes import plain_passes
from atrium.retrieve.verified_pages import verified_pages
from atrium.retrieve.word_verifiers import word_verifiers
from atrium.retrieve.workspace_clause import workspace_clause

# FTS5 bm25() returns MORE NEGATIVE values for better matches. Negating it here
# means every lane in this package reports "higher is better", so fusion does not
# have to special-case one lane's sign.
_QUERY = """
SELECT r.record_id, r.text, -bm25(words) AS score, r.conversation_id,
       r.source_sha256, r.authored_at, r.provider, r.role
FROM words
JOIN records r ON r.rowid = words.rowid
WHERE words MATCH ?{scope}
ORDER BY words.rank
"""


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
    statement = _QUERY.format(scope=scope)
    verifiers, has_plain_term = word_verifiers(query)
    conjunction = conjunctive_expression(query)
    if has_plain_term or not verifiers:
        return plain_passes(
            connection, statement, scope_parameters, conjunction, match, limit, exhausted
        )
    return verified_pages(
        connection, statement, scope_parameters, conjunction, match, limit, verifiers, exhausted
    )
