"""Word-level lexical retrieval -- the exact-recall lane."""

import re
import sqlite3

from atrium.retrieve.conjunctive_expression import conjunctive_expression
from atrium.retrieve.fold import fold
from atrium.retrieve.hit import Hit
from atrium.retrieve.plain_passes import plain_passes
from atrium.retrieve.query_terms import query_terms
from atrium.retrieve.verified_pages import verified_pages
from atrium.retrieve.workspace_scope import workspace_clause

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
    match = _match_expression(query)
    if not match:
        return []
    scope, scope_parameters = workspace_clause(workspace)
    statement = _QUERY.format(scope=scope)
    verifiers, has_plain_term = _verifiers(query)
    conjunction = conjunctive_expression(query)
    if has_plain_term or not verifiers:
        return plain_passes(
            connection, statement, scope_parameters, conjunction, match, limit, exhausted
        )
    return verified_pages(
        connection, statement, scope_parameters, conjunction, match, limit, verifiers, exhausted
    )


def _match_expression(query: str) -> str:
    """Join the query's terms with OR -- the lane's recall semantics."""
    return " OR ".join(query_terms(query))


def _verifiers(query: str) -> tuple[list[re.Pattern[str]], bool]:
    """Build adjacency checks for punctuated terms, and note plain ones.

    An FTS5 phrase preserves token order but not the punctuation between tokens,
    so the phrase for `3.7.0` also matches `allocate 3 7 0 workers`. Each
    multi-part term therefore gets a regex requiring its parts to be joined by
    punctuation, not whitespace, in the stored text. The filter applies only when
    every term is punctuated: terms are OR-ed, and a hit that fails the regexes
    may still have matched a plain word this function cannot see.

    Patterns are built over diacritic-folded text and must be matched against
    ``fold``-ed text: the index tokenizer removes diacritics, so `café-au-lait`
    finds a stored `cafe-au-lait`, and a verifier comparing raw strings would
    silently throw that legitimate hit away (reproduced by review).
    """
    verifiers = []
    has_plain_term = False
    for raw_term in query.split():
        parts = re.findall(r"[^\W_]+", raw_term, flags=re.UNICODE)
        if not parts:
            continue
        if len(parts) > 1:
            # The separator class is "punctuation": anything that is neither
            # whitespace nor alphanumeric. `_` must be included explicitly --
            # it counts as \w, yet it is exactly what joins snake_case parts.
            joined = r"(?:[^\w\s]|_)+".join(re.escape(fold(part)) for part in parts)
            verifiers.append(re.compile(rf"(?<!\w){joined}(?!\w)", re.IGNORECASE))
        else:
            has_plain_term = True
    return verifiers, has_plain_term
