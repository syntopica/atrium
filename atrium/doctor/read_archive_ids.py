"""Every conversation id the canonical archive currently holds."""

import json
from pathlib import Path


def read_archive_ids(archive: Path) -> set[str]:
    """Stream the archive for ids alone.

    Deliberately not `read_archive`: the doctor needs 30,000 identifiers, not
    30,000 fully parsed conversations, and the difference on a four-gigabyte
    file is what decides whether the check is cheap enough to run every time.
    """
    identifiers: set[str] = set()
    with archive.open(encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            if line.strip():
                identifiers.add(json.loads(line)["id"])
    return identifiers
