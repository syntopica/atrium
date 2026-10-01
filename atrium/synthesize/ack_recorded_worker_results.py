"""Ack the unacknowledged results of a queue that the registry already holds."""

import urllib.parse

from atrium.synthesize.ack_worker_results import ack_worker_results
from atrium.synthesize.worker_http_call import worker_http_call

_PAGE = 100


def ack_recorded_worker_results(queue: str, recorded: set[str]) -> int:
    """Ack every pending result of ``queue`` whose id a registry record carries.

    A pass writes the record before it acks, so a crash between the two leaves
    a result the registry already holds but the worker still offers. The
    episode is skipped as done on the next pass, so nothing else would ever
    ack it: this drain does, and returns how many it acked.
    """
    after, acked = 0, 0
    while True:
        query = urllib.parse.urlencode({"queue": queue, "after": after, "limit": _PAGE})
        rows = worker_http_call("GET", f"/v1/results?{query}")["results"]
        settled = [row for row in rows if row["result_id"] in recorded]
        ack_worker_results(settled)
        acked += len(settled)
        if len(rows) < _PAGE:
            return acked
        after = max(int(row["seq"]) for row in rows)
