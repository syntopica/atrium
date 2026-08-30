"""Commit a write that may be racing another process's long transaction."""

import sqlite3
import time
from collections.abc import Callable

# Ingest holds one write transaction for a whole archive, which on this corpus
# runs for many minutes. busy_timeout only buys 30 seconds, so a writer that
# merely waits will raise while the other one is still perfectly healthy. The
# ladder below waits about twenty minutes in total before giving up.
_BACKOFF = (1, 2, 5, 10, 30, 60, 120, 240, 480, 600)


def commit_with_retry(connection: sqlite3.Connection, write: Callable[[], None]) -> None:
    """Run ``write`` inside a transaction, retrying while the database is locked.

    SQLite in WAL mode allows concurrent readers, never concurrent writers, and
    the jobs here legitimately overlap: an hourly refresh ingests while a drip
    embeds. Failing the whole run for that is wrong -- the other writer will
    finish. A lock that outlasts the ladder is a real problem and still raises.

    Only ``database is locked`` is retried. Every other OperationalError -- a
    corrupt page, a missing table -- propagates immediately.
    """
    for delay in (*_BACKOFF, None):
        try:
            with connection:
                write()
            return
        except sqlite3.OperationalError as error:
            if "locked" not in str(error) or delay is None:
                raise
            time.sleep(delay)
