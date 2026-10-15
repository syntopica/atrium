"""Rewrite the supersession table from the registry's declarations."""

import sqlite3

from atrium.sql.load_sql import load_sql


def replace_supersessions(
    connection: sqlite3.Connection, rows: list[tuple[str, str, str | None]]
) -> None:
    """Replace every row; the caller owns the transaction.

    Whole-table, not incremental: the declarations are few and the registry is
    canonical, so a withdrawn or re-ranked record can never leave a stale mark.
    """
    connection.execute(load_sql("store/delete_all_supersessions"))
    connection.executemany(load_sql("store/insert_supersession"), rows)
