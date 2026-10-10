"""The entry a `pass start` line opens, before its outcome is known."""

import re
from typing import Any

from atrium.ledger.local_log_time import local_log_time
from atrium.status.iso_utc import iso_utc

# Only these flags are kept: the others can name local paths.
_FLAGS = {"producer": re.compile(r"--producer (\S+)"), "model": re.compile(r"--model (\S+)")}


def opened_pass(stamp: str, lane: str, flags: str) -> dict[str, Any]:
    """Return a ``running`` pass with its lane, producer, model and start."""
    started = local_log_time(stamp)
    found = {key: pattern.search(flags) for key, pattern in _FLAGS.items()}
    return {
        "lane": lane,
        **{key: None if match is None else match.group(1) for key, match in found.items()},
        "startedAt": None if started is None else iso_utc(started),
        "finishedAt": None,
        "durationS": None,
        "exitCode": None,
        "state": "running",
        "synthesized": None,
        "skipped": None,
        "failed": None,
        "deferred": None,
        "trivial": None,
    }
