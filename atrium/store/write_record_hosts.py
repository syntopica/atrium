"""Reconcile observing-host metadata independently of record text and vectors."""

import json
import sqlite3
from collections.abc import Iterable

from atrium.record import Record
from atrium.sql.load_sql import load_sql


def write_record_hosts(connection: sqlite3.Connection, records: Iterable[Record]) -> None:
    """Replace known hosts from canonical input; never infer missing labels."""
    for record in records:
        if record.hosts is None:
            connection.execute(load_sql("store/delete_record_hosts"), (record.record_id,))
        else:
            connection.execute(
                load_sql("store/upsert_record_hosts"),
                (record.record_id, json.dumps(record.hosts, ensure_ascii=False)),
            )
