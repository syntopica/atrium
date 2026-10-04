"""List the registry's record files with their modification times, unread."""

import os
import re
from pathlib import Path

_RECORD_NAME = re.compile(r"^[0-9a-f]{32}\.json$")


def scan_record_files(registry: Path) -> list[tuple[float, Path]]:
    """Return ``(mtime, path)`` for every record file, in no particular order.

    One ``scandir`` pass: the registry holds tens of thousands of files, and
    reading them all to find the newest costs seconds where a stat costs
    microseconds. Scratch files of an in-flight write never match the name.
    """
    directory = registry / "records"
    if not directory.is_dir():
        return []
    entries = []
    with os.scandir(directory) as iterator:
        for entry in iterator:
            if _RECORD_NAME.match(entry.name):
                entries.append((entry.stat().st_mtime, Path(entry.path)))
    return entries
