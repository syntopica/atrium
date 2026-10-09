"""Ack the results a queue still offers for one conversation that has nothing left to make."""

import urllib.parse

from atrium.synthesize.ack_worker_results import ack_worker_results
from atrium.synthesize.worker_http_call import worker_http_call

_PAGE = 100


def ack_conversation_results(queue: str, conversation_id: str, owners: dict[str, set[str]]) -> int:
    """Ack every pending result journaled only by ``conversation_id``; return how many.

    A conversation walked first for holding a result can turn out to have every
    episode recorded already -- by another population, or by a pass that wrote
    the record from a kept partial. Nothing re-submits its jobs then, so their
    results held queue slots until the worker expired them (2026-10-04, and 16
    such conversations still on 2026-10-09).

    A job another conversation also submitted is left alone: that conversation
    may still be waiting for it, and acking would make it pay the call again
    (raised by review, 2026-10-09). Such a result expires in the worker instead.
    """
    after, acked = 0, 0
    while True:
        query = urllib.parse.urlencode({"queue": queue, "after": after, "limit": _PAGE})
        rows = worker_http_call("GET", f"/v1/results?{query}")["results"]
        mine = [row for row in rows if owners.get(str(row["job_id"])) == {conversation_id}]
        ack_worker_results(mine)
        acked += len(mine)
        if len(rows) < _PAGE:
            return acked
        after = max(int(row["seq"]) for row in rows)
