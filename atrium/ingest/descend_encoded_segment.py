"""Walk an encoded segment down the real tree, collecting every match."""

import re
from pathlib import Path

_SEPARATOR = re.compile(r"[^A-Za-z0-9]")


def descend_encoded_segment(base: Path, encoded: str) -> list[str]:
    """Return every directory under ``base`` that ``encoded`` can name.

    Every branch is followed rather than the longest one only: a branch that
    consumes the segment but leaves no directory behind is abandoned, and when
    two survive the segment is ambiguous and the caller must not choose.
    """
    if not encoded:
        return [str(base)]
    try:
        entries = [entry for entry in base.iterdir() if entry.is_dir()]
    except OSError:
        return []
    found: list[str] = []
    for entry in entries:
        name = _SEPARATOR.sub("-", entry.name)
        if encoded == name:
            found.append(str(entry))
        elif encoded.startswith(name + "-"):
            found.extend(descend_encoded_segment(entry, encoded[len(name) + 1 :]))
    return found
