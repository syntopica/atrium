"""The job ids whose results a queue still offers this producer."""

import urllib.parse

from atrium.synthesize.worker_http_call import worker_http_call

_PAGE = 100


def pending_worker_jobs(queue: str) -> set[str]:
    """Read every page of ``GET /v1/results``; only ids, never the outputs, leave here."""
    after, jobs = 0, set[str]()
    while True:
        query = urllib.parse.urlencode({"queue": queue, "after": after, "limit": _PAGE})
        rows = worker_http_call("GET", f"/v1/results?{query}")["results"]
        jobs.update(str(row["job_id"]) for row in rows)
        if len(rows) < _PAGE:
            return jobs
        after = max(int(row["seq"]) for row in rows)
