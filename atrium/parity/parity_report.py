"""Compare a test index rebuilt from a materialized export with the live index."""

from pathlib import Path
from typing import Any

from atrium.doctor.fts_consistency import fts_consistency
from atrium.parity.compare_digests import compare_digests
from atrium.parity.record_digests import record_digests
from atrium.parity.vector_ids import vector_ids
from atrium.store.open_store import open_store


def parity_report(test: Path, live: Path) -> dict[str, Any]:
    """Read both indexes read-only and report every difference that matters.

    Records by id and text digest per provider (raw, notes and synthesis
    alike), the probe of both full-text lanes on each side, and which records
    hold a vector. ``equal`` is true only when no record differs and both
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
            )
        finally:
            connection.close()
    records = compare_digests(sides["test"][0], sides["live"][0])
    test_vectors, live_vectors = sides["test"][1], sides["live"][1]
    lanes = {name: side[2].code for name, side in sides.items()}
    differs = any(
        row[kind]["count"]
        for row in records.values()
        for kind in ("only_test", "only_live", "changed")
    )
    return {
        "equal": not differs and all(side[2].severity == "ok" for side in sides.values()),
        "records": records,
        "fts": lanes,
        "vectors": {
            "test": len(test_vectors),
            "live": len(live_vectors),
            "only_live": len(live_vectors - test_vectors),
            "only_test": len(test_vectors - live_vectors),
        },
    }
