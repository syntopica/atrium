"""Read the supersessions of one context answer's candidates."""

import json
import sqlite3

from atrium.context.supersession import Supersession
from atrium.sql.load_sql import load_sql


def read_supersessions(
    connection: sqlite3.Connection, record_ids: list[str]
) -> dict[str, Supersession]:
    """Return each superseded candidate's mark; empty on an index without the table.

    A read-only reader cannot add the table, and an index last opened for
    writing by older code has none. That index has no supersessions to honour,
    which is not a reason to fail the whole answer.
    """
    if not record_ids:
        return {}
    try:
        rows = connection.execute(
            load_sql("context/supersessions_of"), (json.dumps(sorted(set(record_ids))),)
        ).fetchall()
    except sqlite3.OperationalError as error:
        if "no such table" not in str(error):
            raise
        return {}
    return {record_id: Supersession(by, at) for record_id, by, at in rows}
