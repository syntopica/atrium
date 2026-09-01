"""Stream the archive once for ids, and for which of them admit a record."""

import json
from pathlib import Path

from atrium.doctor.archive_admissions import ArchiveAdmissions
from atrium.ingest.to_records import to_records


def read_archive_admissions(archive: Path) -> ArchiveAdmissions:
    """Return every archived id, and the subset the admission rule would index.

    Deliberately not `read_archive`: the doctor needs identifiers and a yes/no,
    not 30,000 fully materialized conversations, and on a four-gigabyte file
    that difference decides whether the check is cheap enough to run every
    time. The admission test costs almost nothing on top -- the line is already
    parsed for its id, and `to_records` is a generator, so asking it for one
    record stops at the first admissible event rather than building them all.
    """
    all_ids: set[str] = set()
    admitting: set[str] = set()
    with archive.open(encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            if not line.strip():
                continue
            conversation = json.loads(line)
            identifier = conversation.get("id")
            if not identifier:
                continue
            all_ids.add(identifier)
            try:
                first = next(iter(to_records(conversation)), None)
            except ValueError:
                # No id or revision hash: ingest would refuse it too, so it
                # cannot be counted as coverage the index is failing to hold.
                continue
            if first is not None:
                admitting.add(identifier)
    return ArchiveAdmissions(all_ids=all_ids, admitting_ids=admitting)
