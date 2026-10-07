"""The `atrium_search` MCP tool."""

from typing import Any

from atrium.adapters.checked_limit import checked_limit
from atrium.adapters.mcp_app import MCP, READ_ONLY
from atrium.adapters.rendered_hits import rendered_hits
from atrium.adapters.resident_embedder import resident_embedder
from atrium.adapters.served_index import INDEX
from atrium.recall.project_workspace import project_workspace
from atrium.retrieve.search import LANES, search
from atrium.store.open_store import open_store


@MCP.tool(annotations=READ_ONLY)
def atrium_search(
    query: str, limit: int = 10, lane: str = "auto", project: str | None = None
) -> list[dict[str, Any]]:
    """Search the conversation archive, curated notes and synthesized episodes.

    Lanes: "auto" fuses lexical and semantic and is the right default; "words"
    is whole-word lexical alone; "substring" matches fragments inside words;
    "dense" is the semantic lane alone. Ask for "dense" when the wording of the
    question shares nothing with the wording of the answer -- fusing a blind
    lexical lane measurably buries the semantic signal.

    ``project`` is a directory: pass one to search only the work done in the
    project containing it, and leave it out to search everything. The archive
    spans unrelated clients and personal work, so a question about one of them
    is usually better asked with a project than without.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
    limit = checked_limit(limit)
    workspace = None
    if project is not None:
        workspace = project_workspace(project)
        if workspace is None:
            raise ValueError(f"{project!r} is in no repository, so it names no project")
    connection = open_store(INDEX, read_only=True)
    try:
        embedder = resident_embedder() if lane in ("auto", "dense") else None
        return rendered_hits(
            search(connection, query, limit, lane, embedder=embedder, workspace=workspace)
        )
    finally:
        connection.close()
