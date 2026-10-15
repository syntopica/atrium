"""The `atrium_remember` MCP tool."""

from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from atrium.adapters.mcp_app import MCP
from atrium.adapters.served_index import INDEX
from atrium.recall.project_workspace import project_workspace
from atrium.remember.remember import remember
from atrium.state.state_directory import state_directory
from atrium.synthesize.default_registry import default_registry
from atrium.telemetry.append_lane_event import append_lane_event

# It writes, so a host must ask; repeating the same statement names the same
# record, which is what makes a retry safe.
WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True)


@MCP.tool(annotations=WRITES)
def atrium_remember(  # noqa: PLR0913 -- the statement's fields are the tool's schema
    project: str,
    title: str,
    summary: str,
    *,
    facts: list[str] | None = None,
    open_ends: list[str] | None = None,
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    """Keep one statement in the project's memory, searchable at once.

    For a decision, a correction, a gotcha or a procedure a later session
    should find: self-contained, naming the files, commands and values it is
    about. Secrets are redacted. ``supersedes`` takes record ids of episodes
    this statement replaces (from atrium_context evidence); they stay
    searchable as history, ranked last and marked with what replaced them.
    """
    append_lane_event(state_directory(), "mcp.remember", "write")
    workspace = project_workspace(project)
    if workspace is None:
        raise ToolError(f"{project!r} is in no repository, so it names no project")
    from atrium.embed.embedder import Embedder

    payload = {
        "title": title,
        "summary": summary,
        "facts": facts or [],
        "open_ends": open_ends or [],
    }
    try:
        return remember(
            payload,
            workspace,
            supersedes=supersedes or [],
            registry=default_registry(),
            index=INDEX,
            embedder=Embedder(),
        )
    except ValueError as error:
        raise ToolError(str(error)) from error
