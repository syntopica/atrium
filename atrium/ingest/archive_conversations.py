"""Stream conversations out of an open canonical archive file."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO


def archive_conversations(
    handle: TextIO, path: Path, manifest: dict[str, Any] | None = None
) -> Iterator[dict[str, Any]]:
    """Yield every conversation line; copy the manifest line into ``manifest``.

    Reading the manifest from the same open file as the conversations is what
    ties them to one version: the archive is replaced by rename, and opening
    the path again could read the next one's manifest. Malformed lines raise.
    """
    for line_number, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number} is not valid JSON") from error
        if payload.get("kind") == "rocket-agents-conversation-export":
            if manifest is not None:
                manifest.update(payload)
            continue
        yield payload
