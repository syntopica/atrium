"""Probe both full-text indexes for postings their records no longer back."""

import sqlite3

from atrium.doctor.finding import Finding
from atrium.sql.load_sql import load_sql


def fts_consistency(connection: sqlite3.Connection) -> Finding:
    """Rank one broad query per index; a posting without its row makes it raise.

    A ranked query reads the size of every row it matches, so a posting left
    for a deleted row fails it with "database disk image is malformed" -- how
    the live index broke on 2026-10-15, answering `index_unavailable` to every
    question that touched it. The full `integrity-check` takes 12 minutes on
    the trigram index; these probes take about 3 s and match ~90% of records,
    and an orphan row is caught when it held any of their common words.
    """
    probes = {
        "words": load_sql("doctor/probe_words"),
        "substrings": load_sql("doctor/probe_substrings"),
    }
    failed = {}
    for table, statement in probes.items():
        try:
            connection.execute(statement).fetchall()
        except sqlite3.DatabaseError as error:
            failed[table] = str(error)
    if failed:
        return Finding(
            check="fts",
            severity="broken",
            code="fts_orphan_postings",
            summary=f"{', '.join(failed)} fails a ranked query; run `atrium repair-index --apply`",
            detail={"failed": failed},
        )
    return Finding(
        check="fts",
        severity="ok",
        code="fts_ranked_probe_passed",
        summary="ranked probes pass on words and substrings",
        detail={},
    )
