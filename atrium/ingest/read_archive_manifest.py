"""Read the manifest line of a canonical export or archive file."""

import json
from pathlib import Path
from typing import Any


def read_archive_manifest(path: Path) -> dict[str, Any]:
    """Return the first line when it is the export manifest, else an empty dict."""
    with path.open(encoding="utf-8") as handle:
        first = handle.readline()
    try:
        payload = json.loads(first)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict) and payload.get("kind") == "rocket-agents-conversation-export":
        return payload
    return {}
