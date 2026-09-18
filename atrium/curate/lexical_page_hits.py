"""The exact-recall lane over curated pages: identifiers, paths, proper names."""

import re
import sqlite3

from atrium.curate.page_candidate import PageCandidate
from atrium.retrieve.fold import fold

# Pages are indexed as chunks under provider `brain`, one record per chunk,
# with the page's relative path in `conversation_id`. Nothing else in the index
# is a curated page, so the provider is the whole scope.
_QUERY = """
SELECT r.conversation_id, r.title, -bm25(words) AS score, r.text
FROM words
JOIN records r ON r.rowid = words.rowid
WHERE words MATCH ? AND r.provider = 'brain'
ORDER BY words.rank
LIMIT ?
"""
# A claim is a sentence, not a query: ANDing its words matches nothing, and
# feeding all of them to OR drowns the rare token that carries the identity.
# The longest terms are the discriminating ones (`selectPendingDrafts`,
# `wrangler.jsonc`), so the expression keeps those and drops the rest.
_TERMS = 12
_MIN_LENGTH = 4


def lexical_page_hits(
    connection: sqlite3.Connection, claim: str, limit: int = 20
) -> list[PageCandidate]:
    """Return curated pages whose text shares rare words with the claim."""
    # Words only, never the raw split: a claim quotes code, and `@types/react`
    # or a path fed to FTS5 fails the whole query with a syntax error rather
    # than matching nothing.
    terms = sorted(
        {
            term
            for term in re.findall(r"[a-z0-9_]+", fold(claim).lower())
            if len(term) >= _MIN_LENGTH
        },
        key=len,
        reverse=True,
    )[:_TERMS]
    if not terms:
        return []
    match = " OR ".join(f'"{term}"' for term in terms)
    return [
        PageCandidate(
            path=row[0], title=row[1], score=float(row[2]), lane="lexical", excerpt=row[3]
        )
        for row in connection.execute(_QUERY, (match, limit)).fetchall()
    ]
