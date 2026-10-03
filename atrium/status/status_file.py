"""Where one named status document lives inside the state directory."""

from pathlib import Path


def status_file(state: Path, name: str) -> Path:
    """Return ``<state>/status/<name>.json``, the path readers poll."""
    return state / "status" / f"{name}.json"
