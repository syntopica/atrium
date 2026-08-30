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


def project_workspace(cwd: str | Path, home: str | Path | None = None) -> str:
    """Return the stored-workspace prefix for the project containing ``cwd``.

    Returned as a prefix rather than a single path because a session's cwd is
    often below the project root -- `p/intelifactu/apps/web` is intelifactu's
    memory, not a project with none of its own. Callers match the prefix and
    everything under it.
    """
    home = Path(home) if home is not None else Path.home()
    path = Path(cwd).expanduser()
    try:
        text = f"{_HOME}/{path.relative_to(home)}"
    except ValueError:
        text = str(path)
    return _WORKTREE.sub("", text).rstrip("/")
