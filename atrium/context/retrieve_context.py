"""The shared, read-only context operation for CLI and resident MCP."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atrium.context.context_hits import context_hits
from atrium.context.context_indexes_ready import context_indexes_ready
from atrium.context.context_response import context_response
from atrium.context.finalize_context import finalize_context
from atrium.context.lazy_embedder import LazyEmbedder
from atrium.context.linked_hits import linked_hits
from atrium.context.select_evidence import select_evidence
from atrium.context.validate_request import validate_request
from atrium.context.vector_presence import vector_presence
from atrium.recall.project_workspace import project_workspace
from atrium.retrieve.hit import Hit
from atrium.store.verify_build_stamp import verify_build_stamp

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder


def retrieve_context(  # noqa: PLR0913 -- single shared public adapter contract
    connection: sqlite3.Connection,
    query: str,
    *,
    project: str | Path | None = None,
    limit: int = 8,
    max_chars: int = 16000,
    lane: str = "auto",
    embedder: "ContextEmbedder | None" = None,
    state: Path | None = None,
) -> dict[str, Any]:
    """Combine scoped history with curated notes and bounded indexed links.

    ``max_chars`` bounds evidence text, not the JSON provenance envelope. Notes
    have a separate role-filtered pass using the same adaptive fusion; existing
    history fusion and embedding choices remain unchanged. No link reads files.
    """
    validate_request(query, limit, max_chars, lane)
    workspace = project_workspace(project) if project is not None else None
    if project is not None and workspace is None:
        raise ValueError(f"{project!r} is in no repository, so it names no project")
    response = context_response(query, project, workspace, limit, max_chars, lane, state)
    depth = limit * 4
    try:
        verify_build_stamp(connection, stamp_if_empty=False)
        if not context_indexes_ready(connection):
            response["warnings"].append("context_indexes_missing_run_prepare_context")
            response["index_status"] = "unavailable"
            return finalize_context(response)
        response["index_status"] = (
            "ready" if connection.execute("SELECT 1 FROM records LIMIT 1").fetchone() else "empty"
        )
        if lane in ("auto", "dense"):
            for name, curated in (("history", False), ("curated", True)):
                if not vector_presence(connection, curated=curated, workspace=workspace):
                    response["route"][f"{name}_lane"] = "words"
                    response["warnings"].append(f"{name}_vectors_missing_lexical_fallback")
        active_embedder = embedder if embedder is not None else LazyEmbedder()
        try:
            notes = context_hits(
                connection,
                query,
                depth,
                response["route"]["curated_lane"],
                active_embedder,
                curated=True,
            )
            history = context_hits(
                connection,
                query,
                depth,
                response["route"]["history_lane"],
                active_embedder,
                curated=False,
                workspace=workspace,
            )
        except (OSError, RuntimeError, ValueError):
            if lane not in ("auto", "dense"):
                raise
            notes = context_hits(connection, query, depth, "words", None, curated=True)
            history = context_hits(
                connection, query, depth, "words", None, curated=False, workspace=workspace
            )
            response["route"]["curated_lane"] = "words"
            response["route"]["history_lane"] = "words"
            response["warnings"].append("semantic_unavailable_lexical_fallback")
        links, warnings = linked_hits(connection, notes[:limit], depth)
        response["warnings"].extend(warnings)
        response["steps"] = [
            {
                "pass": "history",
                "scope": workspace or "all_history_explicit_unscoped",
                "lane": response["route"]["history_lane"],
                "candidates": len(history),
                "candidate_limit": depth,
            },
            {
                "pass": "curated",
                "scope": "curated_notes_in_selected_index",
                "lane": response["route"]["curated_lane"],
                "candidates": len(notes),
                "candidate_limit": depth,
            },
            {
                "pass": "links",
                "scope": "one_hop_indexed_curated_same_provider",
                "lane": "linked",
                "candidates": len(links),
                "candidate_limit": depth,
                "root_limit": limit,
                "targets_per_root_limit": 50,
            },
        ]
        candidates: list[tuple[Hit, str, str | None]] = []
        for position in range(max(len(history), len(notes), len(links))):
            if position < len(history):
                candidates.append((history[position], "history", None))
            if position < len(notes):
                candidates.append((notes[position], "curated", None))
                candidates.extend(
                    (hit, "link", parent)
                    for hit, parent in links
                    if parent == notes[position].record_id
                )
        select_evidence(candidates, response)
    except (sqlite3.Error, RuntimeError, OSError):
        response["index_status"] = "unavailable"
        response["warnings"].append("index_unavailable_or_incompatible")
    return finalize_context(response)
