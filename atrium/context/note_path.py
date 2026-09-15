"""Validate indexed note paths as portable relative identifiers."""

from pathlib import PurePosixPath


def note_path(value: str) -> str | None:
    """Reject filesystem escapes and URI-like identifiers without reading files."""
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or ":" in value
        or "\\" in value
        or "\x00" in value
    ):
        return None
    if path.suffix.lower() != ".md":
        return None
    return str(path)
