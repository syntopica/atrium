"""Keep an erasure's identifiers on disk until every store is scrubbed."""

import json
import os
from collections.abc import Collection
from pathlib import Path


def journaled_identifiers(journal: Path, found: Collection[str]) -> set[str]:
    """Return ``found`` plus whatever an earlier, interrupted run recorded.

    Each store the erasure cleans is also where some of its identifiers came
    from: the registry files give the job keys, the candidate ledger gives the
    candidate ids. A run that failed after cleaning one of them could not find
    those ids again, so they are written here before anything is deleted and
    the caller removes the journal only once the run completed.
    """
    known = set(found)
    if journal.is_file():
        known.update(json.loads(journal.read_text(encoding="utf-8")))
    temporary = journal.with_name(f".{journal.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(sorted(known)), encoding="utf-8")
    temporary.replace(journal)
    return known
