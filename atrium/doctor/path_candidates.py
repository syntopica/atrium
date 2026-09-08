"""Every PATH entry that holds something by a given name, in shell order."""

import os
from pathlib import Path


def path_candidates(name: str, search_path: str) -> list[Path]:
    """Return each entry of ``search_path`` holding ``name``, earliest first.

    Deliberately not ``shutil.which``: which answers "is there something
    runnable", skipping an unusable candidate as if nothing were there. The
    caller has to see what it skipped in order to report the shadow, so every
    candidate is returned and the judgement is made one layer up.

    ``Path.lexists`` semantics are wanted here -- a dangling symlink is a
    candidate the shell finds and then fails on -- so the test is on the
    directory entry, not on the target.
    """
    found: list[Path] = []
    for entry in search_path.split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / name
        if candidate.exists() or candidate.is_symlink():
            found.append(candidate)
    return found
