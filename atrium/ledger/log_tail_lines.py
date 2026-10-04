"""The last lines of a log, read from its end so its length does not matter."""

from pathlib import Path


def log_tail_lines(path: Path, max_bytes: int = 262_144) -> list[str]:
    """Return the complete lines inside the final ``max_bytes`` of ``path``.

    A missing log is an empty list. The first line of a partial read is
    dropped, since it starts mid-line.
    """
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, 2)
            handle.seek(max(0, size - max_bytes))
            data = handle.read()
    except OSError:
        return []
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[1:] if size > max_bytes else lines
