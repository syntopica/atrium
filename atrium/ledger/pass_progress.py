"""How far the running pass has got, from the lines it prints per conversation."""

import re
from pathlib import Path
from typing import Any

from atrium.status.iso_utc import iso_utc

_DONE = re.compile(r"^\s+\[\d+/(\d+)\] \S+ \+(\d+) \(skipped \d+\)$")
_FAILED = re.compile(r"^\s+\[\d+/(\d+)\] \S+ FAILED: ")
_WALL = re.compile(r"^\s+\[\d+/\d+\] (quota wall|queue full)")


def pass_progress(log: Path) -> dict[str, Any] | None:
    """Count finished and failed conversations and records made so far.

    Counts only, never the failure text: an exception message can quote the
    conversation it failed on. ``None`` when the pass has printed nothing.
    """
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        updated = log.stat().st_mtime
    except OSError:
        return None
    total = finished = failed = synthesized = 0
    walled = False
    for line in lines:
        done = _DONE.match(line)
        broken = _FAILED.match(line)
        if done is not None:
            total = int(done.group(1))
            finished += 1
            synthesized += int(done.group(2))
        elif broken is not None:
            total = int(broken.group(1))
            failed += 1
        elif _WALL.match(line) is not None:
            walled = True
    if not lines:
        return None
    return {
        "conversations": total,
        "finished": finished,
        "failed": failed,
        "synthesized": synthesized,
        "walled": walled,
        "updatedAt": iso_utc(updated),
    }
