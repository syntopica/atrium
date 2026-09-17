"""Read back JSONL lines by byte offset."""

import json
from pathlib import Path
from typing import Any


def records_at_offsets(path: Path, offsets: list[int]) -> list[dict[str, Any]]:
    """Return the records at the given byte offsets, in the order asked for.

    Seeking beats a second full scan: the sample is a few hundred lines out of
    a ledger of hundreds of thousands, and the first pass already knows where
    each one starts.
    """
    records = []
    with path.open("rb") as handle:
        for offset in offsets:
            handle.seek(offset)
            records.append(json.loads(handle.readline()))
    return records
