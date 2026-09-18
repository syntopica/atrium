"""Read a JSONL ledger, tolerating one that has not been written yet."""

import json
from pathlib import Path
from typing import Any


def jsonl_rows(path: Path) -> list[dict[str, Any]]:
    """Return the rows of ``path``, or none when the file is absent."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
