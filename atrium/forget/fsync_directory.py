"""Persist a directory's entries, so a file just created in it survives a power cut."""

import os
from pathlib import Path


def fsync_directory(directory: Path) -> None:
    """Fsync ``directory`` itself; a file's own fsync does not cover its name."""
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
