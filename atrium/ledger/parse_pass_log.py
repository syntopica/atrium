"""Turn the synthesis wrapper's tick log into one entry per pass."""

import re
from typing import Any

from atrium.ledger.closed_pass import closed_pass
from atrium.ledger.opened_pass import opened_pass

_STAMP = r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)"
_START = re.compile(rf"^{_STAMP} pass start: (\S+)(.*)$")
_DONE = re.compile(rf"^{_STAMP} pass done: (\S+) exit (\d+);(.*)$")


def parse_pass_log(lines: list[str]) -> list[dict[str, Any]]:
    """Return passes oldest first: lane, flags, instants, exit and tallies.

    A start followed by another start never finished: the tick was killed
    before it could log, so it is ``interrupted``. A start with nothing after
    it is still ``running``.
    """
    passes: list[dict[str, Any]] = []
    for line in lines:
        start = _START.match(line)
        if start is not None:
            if passes and passes[-1]["state"] == "running":
                passes[-1]["state"] = "interrupted"
            passes.append(opened_pass(start.group(1), start.group(2), start.group(3)))
            continue
        done = _DONE.match(line)
        if done is None or not passes or passes[-1]["state"] != "running":
            continue
        if passes[-1]["lane"] == done.group(2):
            passes[-1] = closed_pass(passes[-1], done.group(1), int(done.group(3)), done.group(4))
    return passes
