"""The ``<section>.path`` value one configuration file declares, if any."""

import json
from pathlib import Path


def declared_section_path(file: Path, section: str) -> str | None:
    """Return the declared string, or None when the file or key is absent.

    A missing or unreadable file contributes nothing rather than raising:
    this decides where data lives, and the schema-checking engines, not this
    reader, are where a malformed instance is reported.
    """
    try:
        document = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    block = document.get(section) if isinstance(document, dict) else None
    value = block.get("path") if isinstance(block, dict) else None
    return value if isinstance(value, str) and value else None
