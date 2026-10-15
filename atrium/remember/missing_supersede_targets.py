"""The supersede targets a remembered statement names that the index does not hold."""

import json
import sqlite3

from atrium.sql.load_sql import load_sql


def missing_supersede_targets(connection: sqlite3.Connection, targets: list[str]) -> list[str]:
    """Return the targets that are not synthesized episodes in the index, sorted."""
    if not targets:
        return []
    present = {
        row[0]
        for row in connection.execute(
            load_sql("remember/present_synthesis_ids"), (json.dumps(sorted(set(targets))),)
        )
    }
    return sorted(set(targets) - present)
