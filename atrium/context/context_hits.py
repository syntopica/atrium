"""Apply existing adaptive fusion separately to each context population."""

import sqlite3
from typing import TYPE_CHECKING

from atrium.context.dense_hits import dense_hits
from atrium.context.dense_matrix_hits import dense_matrix_hits
from atrium.context.dense_matrix_scope import dense_matrix_scope
from atrium.context.lexical_hits import lexical_hits
from atrium.context.vector_presence import vector_presence
from atrium.retrieve.fuse_ranked import fuse_ranked
from atrium.retrieve.hit import Hit
from atrium.retrieve.search_hybrid import _FUSION_DEPTH

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder
    from atrium.context.dense_matrix import DenseMatrix


def context_hits(  # noqa: PLR0913 -- shared scope and lane contract
    connection: sqlite3.Connection,
    query: str,
    limit: int,
    lane: str,
    embedder: "ContextEmbedder | None",
    *,
    curated: bool,
    workspace: str | None = None,
    exhausted: set[str] | None = None,
    dense_matrix: "DenseMatrix | None" = None,
) -> list[Hit]:
    """Preserve 70/30 fusion and its 60-candidate depth without global starvation.

    With ``dense_matrix`` the dense pass ranks a resident copy of the vectors and
    reads only the winners from the index; without it, the index is scanned.
    """
    if lane in ("words", "substring"):
        return lexical_hits(
            connection,
            query,
            limit,
            lane,
            curated=curated,
            workspace=workspace,
            exhausted=exhausted,
        )
    depth = max(_FUSION_DEPTH, limit)
    lexical = (
        lexical_hits(
            connection,
            query,
            depth,
            "words",
            curated=curated,
            workspace=workspace,
            exhausted=exhausted,
        )
        if lane == "auto"
        else []
    )
    present = (
        bool(dense_matrix_scope(dense_matrix, curated=curated, workspace=workspace).any())
        if dense_matrix is not None
        else vector_presence(connection, curated=curated, workspace=workspace)
    )
    if not present:
        return lexical[:limit]
    if embedder is None:
        raise RuntimeError("semantic retrieval requires an embedder")
    vector = embedder.embed([query])[0]
    dense = (
        dense_matrix_hits(
            connection, dense_matrix, vector, depth, curated=curated, workspace=workspace
        )
        if dense_matrix is not None
        else dense_hits(connection, vector, depth, curated=curated, workspace=workspace)
    )
    if not dense:
        return lexical[:limit]
    if not lexical:
        return dense[:limit]
    return fuse_ranked(lexical, dense, limit)
