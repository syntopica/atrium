"""Whether the index still covers what the canonical archive holds."""

import sqlite3

from atrium.doctor.finding import Finding

# The index is derived and disposable, so drift is repaired by ingesting, never
# by editing it. What matters is that drift is visible: an index missing a
# tenth of the corpus answers every query confidently and incompletely.
DRIFT_WARN_RATIO = 0.01
DRIFT_BROKEN_RATIO = 0.05


def index_coverage(connection: sqlite3.Connection, archive_ids: set[str]) -> Finding:
    """Compare the conversations the index holds with the archive's."""
    indexed = {
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT conversation_id FROM records WHERE provider NOT IN ('synthesis', 'brain')"
        )
    }
    missing = archive_ids - indexed
    extra = indexed - archive_ids
    ratio = len(missing) / len(archive_ids) if archive_ids else 0.0
    severity = (
        "broken" if ratio > DRIFT_BROKEN_RATIO else "warn" if ratio > DRIFT_WARN_RATIO else "ok"
    )
    return Finding(
        check="index-coverage",
        severity=severity,
        summary=(
            f"{len(indexed)} of {len(archive_ids)} archived conversations indexed, "
            f"{len(missing)} missing, {len(extra)} indexed but not archived"
        ),
        detail={
            "archived": len(archive_ids),
            "indexed": len(indexed),
            "missing": len(missing),
            "extra": len(extra),
            "missing_sample": sorted(missing)[:20],
        },
    )
