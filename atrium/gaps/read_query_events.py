"""Read the query log's lines for the last few days."""

import json
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def read_query_events(directory: Path, days: int, today: date) -> Iterator[dict[str, Any]]:
    """Yield each logged answer of the last ``days`` days, oldest first.

    A torn or foreign line is skipped, not fatal: the log is appended by
    concurrent processes, and one bad line must not hide a week of questions.
    """
    for offset in range(days - 1, -1, -1):
        path = directory / f"{(today - timedelta(days=offset)).isoformat()}.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event
