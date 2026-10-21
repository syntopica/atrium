"""Read host provenance in bounded batches without migrating reader connections."""

import json
import sqlite3
from collections.abc import Iterable

from atrium.sql.load_sql import load_sql


def read_record_hosts(
    connection: sqlite3.Connection, record_ids: Iterable[str]
) -> dict[str, list[str]]:
    """Return only explicitly stored hosts; old indexes have unknown provenance."""
    ids = list(dict.fromkeys(record_ids))
    found: dict[str, list[str]] = {}
    for start in range(0, len(ids), 500):
        batch = ids[start : start + 500]
        try:
            rows = connection.execute(
                load_sql("store/read_record_hosts").format(placeholders=",".join("?" * len(batch))),
                batch,
            )
            found.update((record_id, json.loads(hosts)) for record_id, hosts in rows)
        except sqlite3.OperationalError as error:
            if "no such table: record_hosts" not in str(error):
                raise
            return {}
    return found
