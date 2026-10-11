"""Aggregate bounded daily lane logs."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


def aggregate_lane_usage(state: Path, days: int, today: date | None = None) -> dict[str, Any]:
    """Count valid events and expose coverage gaps within the requested window."""
    end = today or datetime.now(UTC).date()
    start = end - timedelta(days=days - 1)
    counts = dict.fromkeys(("auto", "words", "substring", "dense", "recent"), 0)
    entrypoints: dict[str, int] = {}
    first: str | None = None
    last: str | None = None
    malformed = 0
    unreadable: list[str] = []
    files = 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        path = state / "lane-usage" / f"{day.isoformat()}.jsonl"
        try:
            if not path.exists():
                continue
            files += 1
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                        stamp = event["ts"]
                        lane = event["lane"]
                        entrypoint = event["entrypoint"]
                        if (
                            not isinstance(stamp, str)
                            or not isinstance(entrypoint, str)
                            or lane not in counts
                            or datetime.fromisoformat(stamp).date() != day
                        ):
                            raise ValueError("invalid event")
                    except (ValueError, KeyError, TypeError):
                        malformed += 1
                        continue
                    counts[lane] += 1
                    entrypoints[entrypoint] = entrypoints.get(entrypoint, 0) + 1
                    first = stamp if first is None or stamp < first else first
                    last = stamp if last is None or stamp > last else last
        except (OSError, UnicodeError):
            unreadable.append(day.isoformat())
    events = sum(counts.values())
    return {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "coverage": "partial"
        if malformed or unreadable
        else "none"
        if files == 0
        else "partial"
        if files < days
        else "observed",
        "lower_bound": bool(malformed or unreadable or files < days),
        "files": files,
        "events": events,
        "lanes": counts,
        "entrypoints": entrypoints,
        "first": first,
        "last": last,
        "malformed_lines": malformed,
        "unreadable_files": unreadable,
    }
