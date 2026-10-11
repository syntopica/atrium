"""Resolve a requested project, refusing one that names no repository."""

from pathlib import Path

from atrium.recall.project_workspace import project_workspace


def require_workspace(project: str | Path | None) -> str | None:
    """Return the project's workspace prefix; a path in no repository is a caller error."""
    if project is None:
        return None
    workspace = project_workspace(project)
    if workspace is None:
        raise ValueError(f"{project!r} is in no repository, so it names no project")
    return workspace
