"""The nearest enclosing directory that is a repository."""

from pathlib import Path


def repository_root(path: Path) -> Path | None:
    """The nearest ancestor of ``path`` that contains a ``.git``, itself included.

    ``.git`` is a file rather than a directory inside a worktree, so both are
    accepted: a worktree is still inside its project, and the caller folds the
    worktree suffix away afterwards.
    """
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None
