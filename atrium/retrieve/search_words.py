"""Word-level lexical retrieval -- the exact-recall lane."""

import re
import sqlite3
import unicodedata

from atrium.retrieve.hit import Hit
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
ORDER BY bm25(words), r.record_id
LIMIT ? OFFSET ?
"""

_PAGE = 200


def search_words(
    connection: sqlite3.Connection,
    query: str,
    limit: int = 20,
    workspace: str | None = None,
) -> list[Hit]:
    """Return records matching ``query`` on word boundaries, optionally scoped."""
    match = _match_expression(query)
    if not match:
        return []
    scope, scope_parameters = workspace_clause(workspace)
    statement = _QUERY.format(scope=scope)
    verifiers, has_plain_term = _verifiers(query)
    if has_plain_term or not verifiers:
        parameters = (match, *scope_parameters, limit, 0)
        return _hits(connection.execute(statement, parameters).fetchall())[:limit]
    # Every term is punctuated, so every candidate must pass an adjacency
    # check. Paginate until enough verified hits or the candidates run out: a
    # fixed oversample cannot guarantee recall -- with 60 spaced `3 7 0` rows
    # ranked above the one real `3.7.0`, any finite prefetch under 61 returns
    # nothing (reproduced by review).
    verified: list[Hit] = []
    offset = 0
    while len(verified) < limit:
        rows = connection.execute(statement, (match, *scope_parameters, _PAGE, offset)).fetchall()
        if not rows:
            break
        verified.extend(
            hit for hit in _hits(rows) if any(rx.search(_fold(hit.text)) for rx in verifiers)
        )
        offset += _PAGE
    return verified[:limit]


def _hits(rows: list) -> list[Hit]:
    return [
        Hit(
            record_id=row[0],
            text=row[1],
            score=float(row[2]),
            lane="words",
            conversation_id=row[3],
            source_sha256=row[4],
            authored_at=row[5],
            provider=row[6],
            role=row[7],
        )
        for row in rows
    ]


def _match_expression(query: str) -> str:
    """Build an FTS5 MATCH expression that survives identifiers and versions.

    The index tokenizer splits on punctuation, so `3.7.0` is stored as the three
    adjacent tokens `3 7 0`. Dropping the punctuated term -- or worse, dropping
    every fragment shorter than two characters -- makes a version search return
    nothing at all, in the one lane whose entire purpose is exact recall of
    versions, identifiers and names.

    So a term whose parts were joined by punctuation becomes a PHRASE, which
    matches only where those tokens are adjacent in that order. `3.7.0` finds
    `3.7.0` and not a document that merely mentions 3, 7 and 0 apart.

    Everything is quoted, so a query like `mempalace_delete_drawers()` is a
    search rather than an FTS5 syntax error.
    """
    expressions = []
    for raw_term in query.split():
        parts = re.findall(r"[^\W_]+", raw_term, flags=re.UNICODE)
        if not parts:
            continue
        if len(parts) > 1:
            expressions.append('"' + " ".join(parts) + '"')
        elif len(parts[0]) > 1 or len(raw_term) > len(parts[0]):
            # A one-character part is kept only when punctuation was stripped
            # from around it, which is what distinguishes `C#` from a stray `a`.
            expressions.append(f'"{parts[0]}"')
    return " OR ".join(expressions)


def _verifiers(query: str) -> tuple[list[re.Pattern], bool]:
    """Build adjacency checks for punctuated terms, and note plain ones.

    An FTS5 phrase preserves token order but not the punctuation between tokens,
    so the phrase for `3.7.0` also matches `allocate 3 7 0 workers`. Each
    multi-part term therefore gets a regex requiring its parts to be joined by
    punctuation, not whitespace, in the stored text. The filter applies only when
    every term is punctuated: terms are OR-ed, and a hit that fails the regexes
    may still have matched a plain word this function cannot see.

    Patterns are built over diacritic-folded text and must be matched against
    ``_fold``-ed text: the index tokenizer removes diacritics, so `café-au-lait`
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
            joined = r"(?:[^\w\s]|_)+".join(re.escape(_fold(part)) for part in parts)
            verifiers.append(re.compile(rf"(?<!\w){joined}(?!\w)", re.IGNORECASE))
        else:
            has_plain_term = True
    return verifiers, has_plain_term


def _fold(text: str) -> str:
    """Strip diacritics the way the index tokenizer does (remove_diacritics 2)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))
