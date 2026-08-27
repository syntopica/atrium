"""Word-level lexical retrieval — the exact-recall lane."""

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
    terms = [t for t in _tokenize(query) if t]
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
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


def _tokenize(query: str) -> list[str]:
    """Split a query into FTS-safe terms.

    Quoting each term and dropping punctuation keeps a query like
    `mempalace_delete_drawers()` from being read as FTS5 syntax, which is a
    parse error rather than a search.
    """
    cleaned = "".join(char if char.isalnum() or char in "_-" else " " for char in query)
    return [term for term in cleaned.split() if len(term) > 1]
