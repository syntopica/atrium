"""Every record in the synthesis registry."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_records(registry: Path) -> Iterator[dict[str, Any]]:
    """Yield every record in the registry, in deterministic filename order."""
    directory = registry / "records"
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.json")):
        yield json.loads(path.read_text())
