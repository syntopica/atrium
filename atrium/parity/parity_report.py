"""Compare a test index rebuilt from a materialized export with the live index."""

from pathlib import Path
from typing import Any

from atrium.doctor.fts_consistency import fts_consistency
from atrium.parity.compare_digests import compare_digests
from atrium.parity.fts_row_counts import fts_row_counts
from atrium.parity.record_digests import record_digests
from atrium.parity.vector_ids import vector_ids
from atrium.store.open_store import open_store


def parity_report(test: Path, live: Path) -> dict[str, Any]:
    """Read both indexes read-only and report every difference that matters.

    Records by id, provider and text digest (raw, notes and synthesis alike);
    on each side the ranked probe of both full-text lanes and their docsize row
    counts against the records; and which records hold a vector. ``equal`` is true only when no record differs and both
    sides' lanes pass; vectors are reported but not required, since a rebuilt
    test index is usually not embedded.
    """
    sides = {}
    for name, path in (("test", test), ("live", live)):
        connection = open_store(path, read_only=True)
        try:
            sides[name] = (
                record_digests(connection),
                vector_ids(connection),
                fts_consistency(connection),
                fts_row_counts(connection),
            )
        finally:
            connection.close()
    records = compare_digests(sides["test"][0], sides["live"][0])
    test_vectors, live_vectors = sides["test"][1], sides["live"][1]
    lanes = {name: {"probe": side[2].code} | side[3] for name, side in sides.items()}
    lanes_whole = all(
        side[2].severity == "ok" and side[3]["words"] == side[3]["substrings"] == side[3]["records"]
        for side in sides.values()
    )
    differs = any(
        row[kind]["count"]
        for row in records.values()
        for kind in ("only_test", "only_live", "changed")
    )
    return {
        "equal": not differs and lanes_whole,
        "records": records,
        "fts": lanes,
        "vectors": {
            "test": len(test_vectors),
            "live": len(live_vectors),
            "only_live": len(live_vectors - test_vectors),
            "only_test": len(test_vectors - live_vectors),
        },
    }
