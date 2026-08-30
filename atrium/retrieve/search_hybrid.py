"""Adaptive retrieval: fuse when the lexical lane sees something, not before."""

import sqlite3

from atrium.embed.embedder import Embedder
from atrium.retrieve.fuse_ranked import fuse_ranked
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_dense import search_dense
from atrium.retrieve.search_words import search_words

# Each lane contributes this many candidates to fusion regardless of the
# requested output size. Reusing `limit` as the candidate depth returns wrong
# top results: with limit=1, a record ranked second in BOTH lanes -- which full
# RRF ranks first -- is never even fetched (reproduced by review).
_FUSION_DEPTH = 60


def search_hybrid(
    connection: sqlite3.Connection,
    embedder: Embedder,
    query: str,
    limit: int = 20,
    workspace: str | None = None,
) -> list[Hit]:
    """Route between lanes by what the query gives each one to work with.

    The rule comes from measurement, not taste: when the query shares words
    with its answer, fusion beats either lane alone (R@10 80.0% vs 77.3%
    lexical); when it shares none, lexical scores 0% and fusing it in buries
    the dense signal (12% -> 8%). So an empty lexical result routes to dense
    alone, and an empty dense layer (nothing embedded yet) degrades to
    lexical rather than failing.
    """
    depth = max(limit, _FUSION_DEPTH)
    lexical = search_words(connection, query, depth, workspace)
    if not connection.execute("SELECT 1 FROM vectors LIMIT 1").fetchone():
        return lexical[:limit]
    dense = search_dense(connection, embedder.embed([query])[0], depth, workspace)
    if not dense:
        return lexical[:limit]
    if not lexical:
        return dense[:limit]
    return fuse_ranked(lexical, dense, limit)
