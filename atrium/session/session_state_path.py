"""Where one session's checkpoint state lives inside the instance."""

import hashlib
from collections.abc import Mapping
from pathlib import Path

from atrium.state.state_directory import state_directory


def session_state_path(session_id: str, environ: Mapping[str, str] | None = None) -> Path:
    """Return ``<state>/session-record/<sha256(session_id)[:16]>.json``.

    The name is derived, never taken from input: a session id is a string a
    hook payload hands over, and a filename built from it would be a path.
    Under the instance's state directory, two instances never share a file.
    """
    if not session_id:
        raise ValueError("a session state path needs a session id")
    digest = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return state_directory(environ) / "session-record" / f"{digest}.json"
