"""Check the index against the segment archive's current generation."""

import sqlite3
from typing import Any

from atrium.doctor.finding import Finding
from atrium.store.read_archive_generation import read_archive_generation


def archive_generation_freshness(
    connection: sqlite3.Connection, inventory: dict[str, Any]
) -> Finding:
    """Warn when scribe holds another generation or undelivered conversations.

    ``inventory`` is `scribe segments-inventory` output. A different
    generation means an erasure or a reseed the index has not been rebuilt
    from; pending deliveries are conversations captured but not yet handed to
    `ingest --partial`. Either way the index still answers, from a world one
    step behind, so this warns rather than fails.
    """
    indexed = read_archive_generation(connection)
    current = inventory.get("generationId")
    pending = int(inventory.get("pendingDeliveries") or 0)
    detail = {"indexed": indexed, "current": current, "pendingDeliveries": pending}
    if indexed != current:
        return Finding(
            check="archive-generation",
            severity="warn",
            code="archive_generation_stale",
            summary=f"index built from generation {indexed}; scribe holds {current}",
            detail=detail,
        )
    if pending:
        return Finding(
            check="archive-generation",
            severity="warn",
            code="archive_deliveries_pending",
            summary=f"{pending} conversation(s) captured but not yet ingested",
            detail=detail,
        )
    return Finding(
        check="archive-generation",
        severity="ok",
        code="archive_generation_current",
        summary=f"index built from the current generation {current}",
        detail=detail,
    )
