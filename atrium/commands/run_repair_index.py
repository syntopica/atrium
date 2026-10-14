"""The `repair-index` handler of the atrium CLI."""

import json
import time
from pathlib import Path
from typing import Any

from atrium.erase.hold_locks import hold_locks
from atrium.store.fts_integrity_error import fts_integrity_error
from atrium.store.open_store import open_store
from atrium.store.rebuild_fts import rebuild_fts


def run_repair_index(index: Path, state: Path, *, apply: bool) -> int:
    """Check both full-text indexes against ``records``; rebuild a failing one.

    Reports first and rebuilds only with ``apply``, holding the refresh lock so
    no ingest writes while an index is rebuilt from the content table. Exits 1
    while an index is still inconsistent, so a scheduled caller can alert.
    """
    tables: dict[str, dict[str, Any]] = {"words": {}, "substrings": {}}
    try:
        with hold_locks([state / "refresh.lock"]):
            connection = open_store(index)
            try:
                for table, result in tables.items():
                    started = time.monotonic()
                    result["error"] = fts_integrity_error(connection, table)
                    result["check_s"] = round(time.monotonic() - started, 1)
                    if apply and result["error"] is not None:
                        started = time.monotonic()
                        rebuild_fts(connection, table)
                        result["rebuild_s"] = round(time.monotonic() - started, 1)
                        result["error"] = fts_integrity_error(connection, table)
                        result["rebuilt"] = True
            finally:
                connection.close()
    except BlockingIOError:
        print("refused: a refresh holds the instance; run again after it")
        return 3
    print(json.dumps({**tables, "applied": apply}, sort_keys=True))
    return 1 if any(result["error"] for result in tables.values()) else 0
