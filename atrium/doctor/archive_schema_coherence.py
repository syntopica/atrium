"""Whether the archive's manifest agrees with the records beneath it."""

import json
from pathlib import Path

from atrium.doctor.finding import Finding


def archive_schema_coherence(archive: Path, sample: int = 2000) -> Finding:
    """Compare the manifest's schema version with the records it covers.

    A manifest states a schema version, so nothing under it may be older: a
    reader that trusts the header assumes qualified event ids and finds
    unqualified ones. This exact state existed on 2026-08-31 -- manifest
    version 2 over 30,728 version 1 records -- and nothing reported it. The
    check samples rather than reads four gigabytes, because one older record is
    already the whole finding.
    """
    if not archive.exists():
        return Finding(
            check="archive-schema",
            severity="broken",
            summary="the canonical archive does not exist",
            detail={"archive": str(archive)},
        )
    with archive.open(encoding="utf-8") as handle:
        manifest = json.loads(handle.readline())
        declared = manifest.get("schemaVersion")
        older = 0
        seen = 0
        for line in handle:
            if seen >= sample:
                break
            seen += 1
            if json.loads(line).get("schemaVersion", 1) < declared:
                older += 1
    if older:
        return Finding(
            check="archive-schema",
            severity="broken",
            summary=f"{older} of {seen} sampled records predate the manifest's schema {declared}",
            detail={"declared": declared, "older": older, "sampled": seen},
        )
    return Finding(
        check="archive-schema",
        severity="ok",
        summary=f"{seen} sampled records all match manifest schema {declared}",
        detail={"declared": declared, "sampled": seen},
    )
