"""Stamp a new index with its build versions, or refuse a mismatched one."""

import sqlite3

from atrium.store.build_versions import BUILD_VERSIONS


def verify_build_stamp(connection: sqlite3.Connection, *, stamp_if_empty: bool) -> None:
    """Compare the index's recorded build versions against this code's.

    A silent mismatch is the failure this exists to prevent: `CREATE TABLE IF
    NOT EXISTS` happily reuses an index built by an older tokenizer or admission
    rule, and two machines then converge on the same archive but different
    memory. The index is derived and disposable, so a mismatch is never
    migrated -- the caller is told to delete it and re-ingest.
    """
    try:
        stored = dict(connection.execute("SELECT key, value FROM build_metadata"))
    except sqlite3.OperationalError as error:
        # Only a missing table means "unversioned". Every other operational
        # fault -- a locked database, an unreadable file, a failing disk -- is
        # transient or environmental, and answering it with "delete it and
        # re-ingest" hands an agent a destructive instruction for a problem
        # that deleting cannot fix.
        if "no such table" not in str(error):
            raise
        raise RuntimeError(
            "this index has no build_metadata table; it predates index "
            "versioning -- delete it and re-ingest"
        ) from error

    if not stored:
        populated = connection.execute("SELECT 1 FROM records LIMIT 1").fetchone()
        if not stamp_if_empty or populated:
            # A populated index with no stamp predates versioning (or lost its
            # metadata); adopting and stamping it would launder unknown-pipeline
            # content as current. Refusing is cheap -- the index is disposable.
            raise RuntimeError(
                "this index was never stamped with build versions -- delete it and re-ingest"
            )
        connection.executemany(
            "INSERT INTO build_metadata (key, value) VALUES (?, ?)",
            sorted(BUILD_VERSIONS.items()),
        )
        return

    if stored != BUILD_VERSIONS:
        raise RuntimeError(
            f"this index was built by a different pipeline (index: {stored}, "
            f"code: {BUILD_VERSIONS}) -- delete it and re-ingest"
        )
