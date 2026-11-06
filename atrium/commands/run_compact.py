"""The `compact` handler of the atrium CLI."""

import json
import time
from pathlib import Path
from typing import Any

from atrium.erase.erase_lock_file import erase_lock_file
from atrium.erase.hold_locks import hold_locks
from atrium.sql.load_sql import load_sql
from atrium.store.open_store import open_store
from atrium.store.rebuild_fts import rebuild_fts


def run_compact(index: Path, state: Path, *, apply: bool) -> int:
    """Rebuild both full-text lanes from ``records`` and VACUUM the file.

    FTS5 keeps a deleted row's postings until its segments merge, and VACUUM
    alone cannot drop them, so the 2026-10-14 admission cut (1.9M records to
    484k) left the file at 23 GB. Measured on an APFS clone on 2026-11-06: the
    two rebuilds and a VACUUM took it from 23,331 MiB to 3,915 MiB in 17 min.
    Reports the size first and writes only with ``apply``, under the refresh
    and erase locks so no writer runs meanwhile; readers keep answering.
    """
    report: dict[str, Any] = {"applied": False, "bytes_before": index.stat().st_size}
    if not apply:
        print(json.dumps(report, sort_keys=True))
        return 0
    try:
        with hold_locks([erase_lock_file(state), state / "refresh.lock"]):
            connection = open_store(index)
            try:
                for table in ("words", "substrings"):
                    started = time.monotonic()
                    rebuild_fts(connection, table)
                    report[f"rebuild_{table}_s"] = round(time.monotonic() - started, 1)
                started = time.monotonic()
                connection.execute(load_sql("store/vacuum"))
                report["vacuum_s"] = round(time.monotonic() - started, 1)
                checkpoint = list(
                    connection.execute(load_sql("store/wal_checkpoint_truncate")).fetchone()
                )
                report["wal_checkpoint"] = checkpoint
            finally:
                connection.close()
    except BlockingIOError:
        print("refused: a writer or a refresh holds the instance; run again after it")
        return 3
    report["applied"] = True
    report["bytes_after"] = index.stat().st_size
    print(json.dumps(report, sort_keys=True))
    if checkpoint[0]:
        print("incomplete: a reader kept the WAL from truncating; run compact again once idle")
        return 4
    return 0
