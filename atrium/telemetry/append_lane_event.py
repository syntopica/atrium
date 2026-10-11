"""Append one privacy-preserving lane usage event."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def append_lane_event(state: Path, entrypoint: str, lane: str) -> None:
    """Record an accepted public request without affecting retrieval on failure."""
    try:
        now = datetime.now(UTC)
        directory = state / "lane-usage"
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / f"{now.date().isoformat()}.jsonl"
        payload = (
            json.dumps({"ts": now.isoformat(), "entrypoint": entrypoint, "lane": lane}) + "\n"
        ).encode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
            if os.write(fd, payload) != len(payload):
                raise OSError("short lane telemetry write")
        finally:
            os.close(fd)
    except OSError as error:
        print(f"atrium lane telemetry unavailable: {error}", file=sys.stderr)
