"""The providers a raw archive ingest has written revisions for."""

import sqlite3

from atrium.sql.load_sql import load_sql


def read_archive_revision_providers(connection: sqlite3.Connection) -> set[str]:
    """Every revision provider except ``synthesis``, which its own ingest owns.

    A full export of a generation can drop a provider entirely -- an erasure of
    the only `trae` conversation leaves none -- and the sweep, keyed by the
    providers the export carries, would then never visit it.
    """
    return {row[0] for row in connection.execute(load_sql("store/read_archive_revision_providers"))}
