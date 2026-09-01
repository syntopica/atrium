"""Retrieval by lane name -- the one entry point every adapter calls."""

import sqlite3
from typing import TYPE_CHECKING

from atrium.retrieve.hit import Hit
from atrium.retrieve.search_substrings import search_substrings
from atrium.retrieve.search_words import search_words

if TYPE_CHECKING:
    from atrium.embed.embedder import Embedder

LANES = ("auto", "words", "substring", "dense")


def search(  # noqa: PLR0913 -- the one shared retrieval surface; every knob is a real caller need
    connection: sqlite3.Connection,
    query: str,
    limit: int,
    lane: str = "auto",
    *,
    embedder: "Embedder | None" = None,
    workspace: str | None = None,
) -> list[Hit]:
    """Return whole hits for ``query`` on ``lane``.

    Adapters -- the CLI, an MCP server, a session-start snapshot writer -- share
    this function rather than each other's output. The CLI's printed form is
    lossy on purpose (it truncates text for a terminal), so an adapter that
    parsed it would serve truncated memory and no caller could tell.

    The embedder is imported lazily and only for the lanes that need one: it
    costs seconds to construct, and the lexical lanes must not pay that. A
    long-lived caller -- an MCP server answering many queries in one process --
    passes its own resident instance instead, so that cost is paid once for the
    life of the process rather than once per query.

    ``workspace`` narrows every lane to one project before it takes its own
    limit, so a scoped search returns that project's best matches rather than
    whatever survives filtering the global top N. Unscoped is the default: a
    question is often about work done elsewhere.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
    if lane == "substring":
        return search_substrings(connection, query, limit, workspace)
    if lane == "words":
        return search_words(connection, query, limit, workspace)

    if embedder is None:
        from atrium.embed.embedder import Embedder

        embedder = Embedder()

    if lane == "dense":
        from atrium.retrieve.search_dense import search_dense

        return search_dense(connection, embedder.embed([query])[0], limit, workspace)

    from atrium.retrieve.search_hybrid import search_hybrid

    return search_hybrid(connection, embedder, query, limit, workspace)
