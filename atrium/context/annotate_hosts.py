"""Attach explicitly indexed observing hosts to structured retrieval evidence."""

import sqlite3
from typing import Any

from atrium.store.read_record_hosts import read_record_hosts


def annotate_hosts(connection: sqlite3.Connection, items: list[dict[str, Any]]) -> None:
    """Keep unknown hosts absent, including on legacy read-only indexes."""
    hosts = read_record_hosts(connection, (item["record_id"] for item in items))
    for item in items:
        if item["record_id"] in hosts:
            item["hosts"] = hosts[item["record_id"]]
