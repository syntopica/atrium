"""Append one context answer to the query log, beside the synthesis registry."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atrium.telemetry.query_event import query_event


def append_query_event(state: Path, response: dict[str, Any], entrypoint: str) -> None:
    """Record the answer without ever affecting it.

    The log lives in the registry directory, not beside the index: the index is
    disposable and a rebuild would erase it, while the registry is the one
    durable directory here and the one the machine sync carries. One file a
    day, owner-only, appended with O_APPEND so concurrent answers interleave by
    whole lines.
    """
    try:
        now = datetime.now(UTC)
        directory = state / "synthesis" / "queries"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / f"{now.date().isoformat()}.jsonl"
        line = json.dumps(query_event(response, entrypoint, now), ensure_ascii=False) + "\n"
        payload = line.encode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(fd, payload) != len(payload):
                raise OSError("short query-log write")
        finally:
            os.close(fd)
    except (OSError, TypeError, ValueError) as error:
        print(f"atrium query log unavailable: {error}", file=sys.stderr)
