"""Where synthesis records live when no path is given: beside the index."""

from pathlib import Path

from atrium.state.state_directory import state_directory


def default_registry() -> Path:
    """Resolve at call time, so the environment and working directory count."""
    return state_directory() / "synthesis"
