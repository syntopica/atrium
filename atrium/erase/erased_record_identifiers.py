"""The job keys and episode ids of the registry records an erasure removes."""

import json
from collections.abc import Iterable
from pathlib import Path


def erased_record_identifiers(files: Iterable[Path]) -> set[str]:
    """Return every ``job_key`` and ``episode_id`` the files carry.

    Curation keys some rows by these rather than by conversation: a quarantined
    fact records only the ``job_key`` of the record it was screened from.
    """
    found: set[str] = set()
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        for key in ("job_key", "episode_id"):
            value = record.get(key)
            if isinstance(value, str) and value:
                found.add(value)
    return found
