"""The project name a workspace path belongs to."""

from pathlib import PurePosixPath

WORKTREES = ".worktrees"


def project_of_workspace(workspace: str | None) -> str | None:
    """Return the project a workspace belongs to, or None when there is none.

    A worktree is the same project as its repository -- `p/bot/.worktrees/
    repo-keeper` is `bot` -- so a claim made in one belongs on the project's
    page rather than on a page named after a branch that no longer exists.
    """
    if not workspace:
        return None
    parts = PurePosixPath(workspace).parts
    if WORKTREES in parts:
        index = parts.index(WORKTREES)
        return parts[index - 1] if index else None
    return parts[-1] if parts else None
