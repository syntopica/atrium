"""The `atrium_recall` MCP tool."""

from typing import Any

from atrium.adapters.checked_limit import checked_limit
from atrium.adapters.mcp_app import MCP, READ_ONLY
from atrium.adapters.rendered_hits import rendered_hits
from atrium.adapters.served_index import INDEX
from atrium.recall.project_workspace import project_workspace
from atrium.recall.recent_episodes import recent_episodes
from atrium.store.open_store import open_store


@MCP.tool(annotations=READ_ONLY)
def atrium_recall(cwd: str, limit: int = 12) -> list[dict[str, Any]]:
    """Return the newest synthesized episodes for the project containing ``cwd``.

    This is not a search: it takes no query. It answers "what has already been
    worked out in this project", which is what a session needs before it knows
    what to ask.

    Returns an empty list when ``cwd`` is in no repository: there is no project
    boundary to recall within, and answering with everything would be worse
    than answering with nothing.
    """
    limit = checked_limit(limit)
    workspace = project_workspace(cwd)
    if workspace is None:
        return []
    connection = open_store(INDEX, read_only=True)
    try:
        return rendered_hits(recent_episodes(connection, workspace, limit))
    finally:
        connection.close()
