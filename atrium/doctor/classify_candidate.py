"""What a PATH entry named like a command actually is, before calling it usable."""

import os
from pathlib import Path

# The reason a candidate is unusable, in the words the operator has to act on.
# `runnable` is the one value that means the shell would execute it.
RUNNABLE = "runnable"


def classify_candidate(candidate: Path) -> str:
    """Say whether ``candidate`` is runnable, and if not, in which way it is not.

    "Exists" is not "resolves". `dotfiles/bootstrap.sh` linked every top-level
    `bin/*` entry, so a fresh machine got `~/.local/bin/atrium` pointing at the
    *directory* holding the wrapper; a wrapper copied instead of linked, or
    restored by a checkout that dropped the mode bit, is a plain file the shell
    refuses; and a symlink whose target moved does not exist at all, which
    reads as "not on PATH" and sends the operator looking for the wrong thing.
    Each is a distinct repair, so each gets a distinct answer.
    """
    if candidate.is_symlink() and not candidate.exists():
        return "is a broken symlink"
    if candidate.is_dir():
        return "is a directory, not the wrapper"
    if not os.access(candidate, os.X_OK):
        return "is not executable"
    return RUNNABLE
