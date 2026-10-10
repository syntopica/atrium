"""Where the resident context service listens for one index's state."""

from pathlib import Path


def context_socket_path(state: Path) -> Path:
    """Place the socket beside the index it serves, in the user's state directory."""
    return state / "context.sock"
