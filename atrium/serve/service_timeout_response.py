"""The honest answer when the resident service ran out of time."""

from pathlib import Path
from typing import Any

from atrium.context.context_response import context_response
from atrium.context.finalize_context import finalize_context
from atrium.recall.project_workspace import project_workspace


def service_timeout_response(  # noqa: PLR0913, PLR0917 -- mirrors the request envelope
    query: str,
    project: Path | None,
    limit: int,
    max_chars: int,
    lane: str,
    state: Path,
) -> dict[str, Any]:
    """Say retrieval did not finish; never let it read as "nothing found"."""
    workspace = project_workspace(project) if project is not None else None
    response = context_response(query, project, workspace, limit, max_chars, lane, state)
    response["index_status"] = "unavailable"
    response["warnings"].append("context_service_timeout")
    return finalize_context(response)
