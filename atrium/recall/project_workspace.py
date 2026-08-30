"""The canonical workspace prefix identifying one project."""

import re
from pathlib import Path

# The exporter redacts the user's home directory before anything is indexed, so
# a live cwd has to be written the same way before it can match a stored path.
_HOME = "[HOME]"

# Two worktree layouts appear in this corpus: `<project>/.claude/worktrees/<x>`
# and a sibling `<project>.worktrees/<x>`. A session in either belongs to the
# project, not to a project of its own -- splitting them would give a branch its
# own memory and hide the trunk's from it.
_WORKTREE = re.compile(r"(?:/\.claude/worktrees/[^/]+|\.worktrees/[^/]+)(?:/.*)?$")


def project_workspace(cwd: str | Path, home: str | Path | None = None) -> str | None:
    """Return the stored-workspace prefix for the project containing ``cwd``.

    A session opened in `p/intelifactu/apps/web` is working on intelifactu and
    must recall intelifactu, so the answer is the project root, not the cwd.
    The root is the nearest enclosing directory holding a `.git` -- the same
    boundary the person is working inside. Callers match that prefix and
    everything under it, so a session at the root and a session three
    directories down share one memory.

    Returns ``None`` when there is no project to name: a path outside any
    repository has no boundary to recall within, and answering with the bare
    path would either match nothing or, for a root path, match everything.
    """
    home = Path(home) if home is not None else Path.home()
    path = Path(cwd).expanduser()
    root = _repository_root(path)
    if root is None:
        return None
    try:
        text = f"{_HOME}/{root.relative_to(home)}"
    except ValueError:
        text = str(root)
    text = _WORKTREE.sub("", text).rstrip("/")
    return text or None


def _repository_root(path: Path) -> Path | None:
    """The nearest ancestor of ``path`` that contains a ``.git``, itself included.

    ``.git`` is a file rather than a directory inside a worktree, so both are
    accepted: a worktree is still inside its project, and the caller folds the
    worktree suffix away afterwards.
    """
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None
