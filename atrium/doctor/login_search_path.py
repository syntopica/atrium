"""The PATH a plain login shell would have, not the one this process inherited."""

import os
import sys
import sysconfig
from pathlib import Path


def login_search_path(search_path: str) -> str:
    """Strip the running interpreter's script directory from ``search_path``.

    Every documented route to this doctor runs it through `uv run --project
    ~/p/atrium`, which prepends `.venv/bin` -- where the `atrium` console
    script exists by construction, because installing the project is what
    creates it. Asking whether the inherited PATH resolves `atrium` therefore
    always says yes, including throughout the outage this check exists to
    catch, when the CLI existed *only* inside that venv and every session that
    followed the agent guidance got `command not found`.

    So the venv's script directory is removed and the question is asked of what
    is left: what a shell that never activated this project would find.
    """
    if sys.prefix == sys.base_prefix:
        # Not in a virtualenv, so there is nothing project-local to hide. The
        # directories the lookup below would name are shared system ones --
        # /opt/homebrew/bin under Homebrew's python, /usr/local/bin under the
        # system one, and ~/.local/bin (the documented install location itself)
        # after a `pip --user` install. Stripping one of those would report a
        # healthy machine as broken, which is the false positive this check
        # already had once.
        return search_path
    hidden = {
        Path(sysconfig.get_path("scripts")).resolve(),
        Path(sys.executable).resolve().parent,
    }
    kept = [
        entry
        for entry in search_path.split(os.pathsep)
        if entry and Path(entry).resolve() not in hidden
    ]
    return os.pathsep.join(kept)
