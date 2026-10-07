"""The `atrium_context` MCP tool."""

from typing import Any

from atrium.adapters.mcp_app import MCP, READ_ONLY
from atrium.adapters.resident_embedder import resident_embedder
from atrium.adapters.served_index import INDEX
from atrium.context.context_from_index import context_from_index
from atrium.context.lazy_embedder import LazyEmbedder
from atrium.state.state_directory import state_directory


@MCP.tool(annotations=READ_ONLY)
def atrium_context(
    query: str,
    project: str | None = None,
    limit: int = 8,
    max_chars: int = 16000,
    lane: str = "auto",
) -> dict[str, Any]:
    """Retrieve scoped history, curated notes and one hop of indexed note links.

    Evidence text shares max_chars (1..100000); limit (1..50) caps evidence
    records. Provenance and warnings are additional JSON metadata. History
    requires live verification before asserting present-day operational results.
    """
    return context_from_index(
        INDEX,
        query,
        project=project,
        limit=limit,
        max_chars=max_chars,
        lane=lane,
        state=state_directory(),
        embedder=LazyEmbedder(resident_embedder),
    )
