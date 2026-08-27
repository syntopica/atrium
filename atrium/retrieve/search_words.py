"""Word-level lexical retrieval — the exact-recall lane."""

import re
import sqlite3

from atrium.retrieve.hit import Hit

# FTS5 bm25() returns MORE NEGATIVE values for better matches. Negating it here
# means every lane in this package reports "higher is better", so fusion does not
# have to special-case one lane's sign.
_QUERY = """
SELECT r.record_id, r.text, -bm25(words) AS score, r.conversation_id,
       r.source_sha256, r.authored_at, r.provider
FROM words
JOIN records r ON r.rowid = words.rowid
WHERE words MATCH ?
ORDER BY bm25(words)
LIMIT ?
"""


def search_words(connection: sqlite3.Connection, query: str, limit: int = 20) -> list[Hit]:
    """Return records matching ``query`` on word boundaries."""
    match = _match_expression(query)
    if not match:
        return []
    rows = connection.execute(_QUERY, (match, limit)).fetchall()
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

    Everything is quoted, so a query like `memstore_delete_drawers()` is a
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
