"""Adaptive retrieval: fuse when the lexical lane sees something, not before."""

import sqlite3

from atrium.embed.embedder import Embedder
from atrium.retrieve.fuse_ranked import fuse_ranked
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_dense import search_dense
from atrium.retrieve.search_words import search_words


def search_hybrid(
    connection: sqlite3.Connection, embedder: Embedder, query: str, limit: int = 20
) -> list[Hit]:
    """Route between lanes by what the query gives each one to work with.

    The rule comes from measurement, not taste: when the query shares words
    with its answer, fusion beats either lane alone (R@10 80.0% vs 77.3%
    lexical); when it shares none, lexical scores 0% and fusing it in buries
    the dense signal (12% -> 8%). So an empty lexical result routes to dense
    alone, and an empty dense layer (nothing embedded yet) degrades to
    lexical rather than failing.
    """
    lexical = search_words(connection, query, limit)
    if not connection.execute("SELECT 1 FROM vectors LIMIT 1").fetchone():
        return lexical
    dense = search_dense(connection, embedder.embed([query])[0], limit)
    if not dense:
        return lexical
    if not lexical:
        return dense
    return fuse_ranked(lexical, dense, limit)
