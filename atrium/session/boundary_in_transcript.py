"""Whether a frozen boundary still exists in the transcript it came from."""

from pathlib import Path


def boundary_in_transcript(path: Path, boundary_uuid: str) -> bool:
    """True when some line of the transcript carries the boundary's uuid.

    A transcript replaced by `/clear`, a resume of another ancestry or a
    truncation no longer holds the uuid, and a checkpoint frozen on it must
    be dropped rather than consumed against material it never named.
    """
    if not boundary_uuid or not path.is_file():
        return False
    needle = boundary_uuid.encode()
    with path.open("rb") as handle:
        return any(needle in line for line in handle)
