"""Whether the index still covers what the canonical archive holds."""

import sqlite3

from atrium.doctor.archive_admissions import ArchiveAdmissions
from atrium.doctor.finding import Finding

# The index is derived and disposable, so drift is repaired by ingesting, never
# by editing it. What matters is that drift is visible: an index missing a
# tenth of the corpus answers every query confidently and incompletely.
DRIFT_WARN_RATIO = 0.01
DRIFT_BROKEN_RATIO = 0.05


def index_coverage(connection: sqlite3.Connection, admissions: ArchiveAdmissions) -> Finding:
    """Compare what the index holds against what the archive could put in it.

    Coverage is measured against the conversations that admit a record, not
    against everything archived. 528 conversations here are archived and index
    to nothing because every event in them is a tool call, a system notice or a
    bare acknowledgement -- that is the admission rule working, and counting it
    as drift made this check warn on every single run. It is still reported,
    because a number that moves is worth seeing; it just is not a defect.
    """
    indexed = {
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT conversation_id FROM records WHERE provider NOT IN ('synthesis', 'brain')"
        )
    }
    missing = admissions.admitting_ids - indexed
    extra = indexed - admissions.all_ids
    admits_nothing = len(admissions.all_ids) - len(admissions.admitting_ids)
    ratio = len(missing) / len(admissions.admitting_ids) if admissions.admitting_ids else 0.0
    severity = (
        "broken" if ratio > DRIFT_BROKEN_RATIO else "warn" if ratio > DRIFT_WARN_RATIO else "ok"
    )
    return Finding(
        check="index-coverage",
        severity=severity,
        summary=(
            f"{len(indexed)} of {len(admissions.admitting_ids)} indexable conversations indexed, "
            f"{len(missing)} missing, {len(extra)} indexed but not archived, "
            f"{admits_nothing} archived conversations admit no record"
        ),
        detail={
            "archived": len(admissions.all_ids),
            "indexable": len(admissions.admitting_ids),
            "indexed": len(indexed),
            "missing": len(missing),
            "extra": len(extra),
            "admits_nothing": admits_nothing,
            "missing_sample": sorted(missing)[:20],
        },
    )
