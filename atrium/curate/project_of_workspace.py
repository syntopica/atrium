"""The project name a workspace path belongs to, when it has one."""

from pathlib import PurePosixPath

WORKTREES = ".worktrees"
# A project needs a root and a name: "/atrium" alone is a path, not a project.
_SHORTEST_PROJECT_PATH = 2
# Where work happens that belongs to no project: the home directory itself, and
# the scratch roots a delegated run is given. Measured on this index, the bare
# home accounts for 4,047 records and the temporary roots for the runs whose
# directory is named `atrium-codex-<random>` -- a project page named after one
# of those would be named after a directory that no longer exists.
TEMPORARY_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")  # noqa: S108


def project_of_workspace(workspace: str | None) -> str | None:
    """Return the project a workspace belongs to, or None when there is none.

    A worktree is the same project as its repository -- `p/bot/.worktrees/
    repo-keeper` is `bot` -- so a claim made in one belongs on the project's
    page rather than on a page named after a branch that no longer exists.

    A hidden directory is refused rather than guessed at: the deepest component
    of `<home>/.wide-project-work/evaldiscrim/out-v19/_codex` is `_codex`, which
    names nothing, and there is no honest way to read a project out of it.
    """
    if not workspace:
        return None
    if workspace.startswith(TEMPORARY_ROOTS):
        return None
    parts = PurePosixPath(workspace).parts
    if WORKTREES in parts:
        index = parts.index(WORKTREES)
        return parts[index - 1] if index >= _SHORTEST_PROJECT_PATH - 1 else None
    if len(parts) < _SHORTEST_PROJECT_PATH:
        return None
    name = parts[-1]
    if name.startswith((".", "_")) or any(part.startswith(".") for part in parts[1:]):
        return None
    return name
