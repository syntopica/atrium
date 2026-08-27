"""Stream conversations out of a canonical rocket-agents archive."""

import json
from pathlib import Path
from typing import Iterator


def read_archive(path: Path) -> Iterator[dict]:
    """Yield every conversation object in a canonical export or archive file.

    The file is JSONL whose first line is a manifest (``kind`` =
    ``rocket-agents-conversation-export``) and whose remaining lines are
    conversations. The manifest is skipped rather than validated here; verifying
    its ``contentSha256`` is layer 1's job, and duplicating that check would give
    Atrium a second opinion about a file it does not own.

    Malformed lines raise. A partially readable archive is a layer 1 defect and
    must not be silently half-ingested: the resulting index would look complete.
    """
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number} is not valid JSON") from error
            if payload.get("kind") == "rocket-agents-conversation-export":
                continue
            yield payload
