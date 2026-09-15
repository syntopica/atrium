"""Apply existing adaptive fusion separately to each context population."""

import sqlite3
from typing import TYPE_CHECKING

from atrium.context.dense_hits import dense_hits
from atrium.context.lexical_hits import lexical_hits
from atrium.context.vector_presence import vector_presence
from atrium.retrieve.fuse_ranked import fuse_ranked
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_hybrid import _FUSION_DEPTH

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder


def context_hits(  # noqa: PLR0913 -- shared scope and lane contract
    connection: sqlite3.Connection,
    query: str,
    limit: int,
    lane: str,
    embedder: "ContextEmbedder | None",
    *,
    curated: bool,
    workspace: str | None = None,
) -> list[Hit]:
    """Preserve 70/30 fusion and its 60-candidate depth without global starvation."""
    if lane in ("words", "substring"):
        return lexical_hits(connection, query, limit, lane, curated=curated, workspace=workspace)
    depth = max(_FUSION_DEPTH, limit)
    lexical = (
        lexical_hits(connection, query, depth, "words", curated=curated, workspace=workspace)
        if lane == "auto"
        else []
    )
    if not vector_presence(connection, curated=curated, workspace=workspace):
        return lexical[:limit]
    if embedder is None:
        raise RuntimeError("semantic retrieval requires an embedder")
    dense = dense_hits(
        connection, embedder.embed([query])[0], depth, curated=curated, workspace=workspace
    )
    if not dense:
        return lexical[:limit]
    if not lexical:
        return dense[:limit]
    return fuse_ranked(lexical, dense, limit)
