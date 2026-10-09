"""The conversations whose synthesis started on an earlier pass and did not finish."""

from pathlib import Path


def started_conversations(partials: Path) -> set[str]:
    """Return the conversation ids that still carry a started marker."""
    directory = partials / "started"
    if not directory.is_dir():
        return set()
    return {path.name for path in directory.iterdir() if path.is_file()}
