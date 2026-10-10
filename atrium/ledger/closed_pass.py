"""Complete an open pass from its `pass done` line."""

import re
from datetime import datetime
from typing import Any

from atrium.ledger.local_log_time import local_log_time
from atrium.ledger.pass_state import pass_state
from atrium.status.iso_utc import iso_utc

_TALLY = re.compile(
    r"synthesized (\d+), already present (\d+), failed conversations (\d+), deferred (\d+)"
)
# Printed since 2026-10-10; an older pass line has none, so its count stays null.
_TRIVIAL = re.compile(r"harness echoes not synthesized (\d+)")


def closed_pass(entry: dict[str, Any], stamp: str, exit_code: int, tail: str) -> dict[str, Any]:
    """Return ``entry`` with its finish, duration, exit state and tallies.

    A pass the time box stopped logs no tally line, so its counts stay null:
    unknown, not zero.
    """
    finished = local_log_time(stamp)
    closed = {**entry, "exitCode": exit_code, "state": pass_state(exit_code)}
    if finished is not None:
        closed["finishedAt"] = iso_utc(finished)
        if entry["startedAt"] is not None:
            started = datetime.fromisoformat(entry["startedAt"]).timestamp()
            closed["durationS"] = max(0, round(finished - started))
    tally = _TALLY.search(tail)
    if tally is not None:
        for index, key in enumerate(("synthesized", "skipped", "failed", "deferred"), start=1):
            closed[key] = int(tally.group(index))
    trivial = _TRIVIAL.search(tail)
    if trivial is not None:
        closed["trivial"] = int(trivial.group(1))
    return closed
