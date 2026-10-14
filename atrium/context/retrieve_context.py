"""The shared, read-only context operation for CLI and resident MCP."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atrium.context.annotate_retired import annotate_retired
from atrium.context.context_hits import context_hits
from atrium.context.context_indexes_ready import context_indexes_ready
from atrium.context.context_response import context_response
from atrium.context.context_steps import context_steps
from atrium.context.demote_retired import demote_retired
from atrium.context.dense_matrix_scope import dense_matrix_scope
from atrium.context.finalize_context import finalize_context
from atrium.context.interleave_candidates import interleave_candidates
from atrium.context.lazy_embedder import LazyEmbedder
from atrium.context.linked_hits import linked_hits
from atrium.context.read_retirements import read_retirements
from atrium.context.rerank_populations import rerank_populations
from atrium.context.retired_mentions import retired_mentions
from atrium.context.select_evidence import select_evidence
from atrium.context.timed import timed
from atrium.context.validate_request import validate_request
from atrium.context.vector_presence import vector_presence
from atrium.forget.forget_ledger_file import forget_ledger_file
from atrium.forget.forgotten_by_term import forgotten_by_term
from atrium.recall.project_workspace import project_workspace
from atrium.sql.load_sql import load_sql
from atrium.store.verify_build_stamp import verify_build_stamp

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder
    from atrium.context.context_reranker import ContextReranker
    from atrium.context.dense_matrix import DenseMatrix


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
    dense_matrix: "DenseMatrix | None" = None,
    reranker: "ContextReranker | None" = None,
) -> dict[str, Any]:
    """Combine scoped history with curated notes and bounded indexed links.

    ``max_chars`` bounds evidence text, not the JSON provenance envelope. Notes
    have a separate role-filtered pass using the same adaptive fusion; existing
    history fusion and embedding choices remain unchanged. No link reads files.
    With ``reranker``, each population's fused candidates are reordered by it
    before links and evidence selection; off unless the caller passes one.
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
            "ready" if connection.execute(load_sql("store/any_record")).fetchone() else "empty"
        )
        if lane in ("auto", "dense"):
            for name, curated in (("history", False), ("curated", True)):
                present = (
                    dense_matrix_scope(dense_matrix, curated=curated, workspace=workspace).any()
                    if dense_matrix is not None
                    else vector_presence(connection, curated=curated, workspace=workspace)
                )
                if not present:
                    response["route"][f"{name}_lane"] = "words"
                    response["warnings"].append(f"{name}_vectors_missing_lexical_fallback")
        active_embedder = embedder if embedder is not None else LazyEmbedder()
        # The word lane's broad pass runs under a wall-clock budget, and an
        # exhausted budget returns nothing. Reported, that is "retrieval ran out
        # of time"; unreported, it is indistinguishable from "this is not in the
        # index", which is the one thing a memory must never say by accident.
        exhausted: set[str] = set()
        # Each pass's wall time, so a slow prompt names the pass that was slow.
        try:
            notes, curated_ms = timed(
                lambda: context_hits(
                    connection,
                    query,
                    depth,
                    response["route"]["curated_lane"],
                    active_embedder,
                    curated=True,
                    exhausted=exhausted,
                    dense_matrix=dense_matrix,
                )
            )
            history, history_ms = timed(
                lambda: context_hits(
                    connection,
                    query,
                    depth,
                    response["route"]["history_lane"],
                    active_embedder,
                    curated=False,
                    workspace=workspace,
                    exhausted=exhausted,
                    dense_matrix=dense_matrix,
                )
            )
        except (OSError, RuntimeError, ValueError):
            if lane not in ("auto", "dense"):
                raise
            notes, curated_ms = timed(
                lambda: context_hits(
                    connection, query, depth, "words", None, curated=True, exhausted=exhausted
                )
            )
            history, history_ms = timed(
                lambda: context_hits(
                    connection,
                    query,
                    depth,
                    "words",
                    None,
                    curated=False,
                    workspace=workspace,
                    exhausted=exhausted,
                )
            )
            response["route"]["curated_lane"] = "words"
            response["route"]["history_lane"] = "words"
            response["warnings"].append("semantic_unavailable_lexical_fallback")
        reranked = None
        if reranker is not None:
            history, notes, reranked = rerank_populations(reranker, query, (history, notes), depth)
            if not reranked["applied"]:
                response["warnings"].append("rerank_unavailable_fused_order")
        (links, warnings), links_ms = timed(lambda: linked_hits(connection, notes[:limit], depth))
        response["warnings"].extend(sorted(exhausted) + warnings)
        response["steps"] = context_steps(
            response,
            workspace,
            depth,
            limit,
            counts=(len(history), len(notes), len(links)),
            times=(history_ms, curated_ms, links_ms),
        )
        if reranked is not None:
            response["steps"].append(reranked)
        candidates = interleave_candidates(history, notes, links)
        retirements = read_retirements(connection)
        mentions = retired_mentions(candidates, retirements)
        select_evidence(demote_retired(candidates, mentions, query), response)
        annotate_retired(
            response, mentions, retirements, lambda: forgotten_by_term(forget_ledger_file())
        )
    except (sqlite3.Error, RuntimeError, OSError):
        response["index_status"] = "unavailable"
        response["warnings"].append("index_unavailable_or_incompatible")
    return finalize_context(response)
