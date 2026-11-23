"""Where the resident context service listens for one index's state."""

import hashlib
from pathlib import Path

# sockaddr_un.sun_path holds 104 bytes on macOS, terminator included.
_SUN_PATH_LIMIT = 103


def context_socket_path(state: Path) -> Path:
    """Place the socket beside the index it serves, in the user's state directory.

    A state directory too deep for a socket address gets one under the home
    directory instead, named after the state so two instances never share it;
    binding the long path died with "AF_UNIX path too long" on every start.
    """
    beside = state / "context.sock"
    if len(str(beside).encode()) <= _SUN_PATH_LIMIT:
        return beside
    digest = hashlib.sha256(str(state).encode()).hexdigest()[:16]
    sockets = Path.home() / ".cache" / "atrium"
    sockets.mkdir(mode=0o700, parents=True, exist_ok=True)
    return sockets / f"{digest}.sock"
