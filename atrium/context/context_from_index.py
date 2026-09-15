"""Open the selected index read-only for a shared adapter request."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atrium.context.context_response import context_response
from atrium.context.retrieve_context import retrieve_context
from atrium.context.validate_request import validate_request
from atrium.recall.project_workspace import project_workspace
from atrium.store.open_store import open_store

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder


def context_from_index(  # noqa: PLR0913 -- shared adapter contract
    index: Path,
    query: str,
    *,
    project: str | Path | None = None,
    limit: int = 8,
    max_chars: int = 16000,
    lane: str = "auto",
    state: Path | None = None,
    embedder: "ContextEmbedder | None" = None,
) -> dict[str, Any]:
    """Turn an unavailable store into explicit structured degradation."""
    validate_request(query, limit, max_chars, lane)
    workspace = project_workspace(project) if project is not None else None
    if project is not None and workspace is None:
        raise ValueError(f"{project!r} is in no repository, so it names no project")
    try:
        connection = open_store(index, read_only=True)
    except (OSError, sqlite3.Error, RuntimeError):
        result = context_response(query, project, workspace, limit, max_chars, lane, state)
        result["index_status"] = "unavailable"
        result["degraded"] = True
        result["warnings"].append("index_unavailable_or_incompatible")
        return result
    try:
        result = retrieve_context(
            connection,
            query,
            project=project,
            limit=limit,
            max_chars=max_chars,
            lane=lane,
            state=state,
            embedder=embedder,
        )
        if state is not None and index.resolve().parent != state.resolve():
            result["freshness"] = {"status": "unknown", "last_refresh": None, "source": None}
            result["warnings"].append("index_state_mismatch")
            result["degraded"] = True
        return result
    finally:
        connection.close()
