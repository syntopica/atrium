"""Publish a JSON document so a reader never sees a partial file."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def publish_json_atomically(target: Path, document: dict[str, Any]) -> None:
    """Write beside ``target``, fsync, then rename over it.

    The temporary file shares the target's directory because a rename is only
    atomic within one filesystem. The directory is fsynced after the rename so
    the new name survives a crash, not only the new bytes. A failure removes
    the temporary file and leaves the previous document in place.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    directory = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
