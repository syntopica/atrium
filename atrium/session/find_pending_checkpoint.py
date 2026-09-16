"""Locate the session state that holds a pending checkpoint by its id."""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from atrium.session.read_session_state import read_session_state
from atrium.state.state_directory import state_directory

_ID = re.compile(r"^[0-9a-f]{16}$")


def find_pending_checkpoint(
    checkpoint_id: str, environ: Mapping[str, str] | None = None
) -> tuple[Path, dict[str, Any]] | None:
    """Return ``(state path, state)`` whose pending checkpoint has this id.

    The id is the only thing the model is told and the only argument it
    passes; everything else (session, transcript, cwd, boundary) comes from
    the state the hook froze. An id that is not sixteen hex digits is
    refused before any directory is read.
    """
    if not _ID.match(checkpoint_id or ""):
        return None
    directory = state_directory(environ) / "session-record"
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("*.json")):
        state = read_session_state(path)
        pending = state.get("pending")
        if isinstance(pending, dict) and pending.get("id") == checkpoint_id:
            return path, state
    return None
