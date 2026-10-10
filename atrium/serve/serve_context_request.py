"""Answer one context request with the resident embedder and matrix."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atrium.context.context_from_index import context_from_index
from atrium.context.read_dense_generation import read_dense_generation
from atrium.store.open_store import open_store

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder
    from atrium.serve.dense_matrix_holder import DenseMatrixHolder


def serve_context_request(
    request: dict[str, Any],
    index: Path,
    holder: "DenseMatrixHolder",
    embedder: "ContextEmbedder",
) -> dict[str, Any]:
    """Run the shared context operation; refuse a request for another index.

    The client names the index it would have opened itself. Answering for a
    different one would be a confident answer from the wrong memory, so a
    mismatch is an error the client resolves by retrieving in-process.
    """
    if Path(request["index"]).resolve() != index.resolve():
        return {"error": "index_mismatch"}
    try:
        connection = open_store(index, read_only=True)
        try:
            live = read_dense_generation(connection)
        finally:
            connection.close()
    except (OSError, sqlite3.Error, RuntimeError):
        live = None
    matrix, warnings = holder.current(live)
    result = context_from_index(
        index,
        request["query"],
        project=request.get("project"),
        limit=request["limit"],
        max_chars=request["max_chars"],
        lane=request["lane"],
        state=Path(request["state"]) if request.get("state") else None,
        embedder=embedder,
        dense_matrix=matrix,
    )
    if warnings:
        result["warnings"].extend(warnings)
        result["degraded"] = True
    return result
