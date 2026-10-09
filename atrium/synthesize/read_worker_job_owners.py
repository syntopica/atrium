"""Read the worker submission journal as job id -> every conversation that submitted it."""

import json
from pathlib import Path


def read_worker_job_owners(journal: Path) -> dict[str, set[str]]:
    """Return each journaled job with all its conversations; a torn line reads as absent.

    Identical text in two conversations is one prompt, so one worker job, and
    the journal holds a line for each conversation that submitted it. Reading
    it as job -> last conversation (`read_worker_submissions`) is enough to find
    a conversation to walk, but not to decide that nobody else needs the result.
    """
    if not journal.exists():
        return {}
    owners: dict[str, set[str]] = {}
    for line in journal.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and "job_id" in entry and "conversation_id" in entry:
            owners.setdefault(str(entry["job_id"]), set()).add(str(entry["conversation_id"]))
    return owners
