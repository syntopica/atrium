"""Read the worker submission journal as job id -> conversation id."""

import json
from pathlib import Path


def read_worker_submissions(journal: Path) -> dict[str, str]:
    """Return every journaled job; a missing journal or a torn line reads as absent."""
    if not journal.exists():
        return {}
    submissions: dict[str, str] = {}
    for line in journal.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and "job_id" in entry and "conversation_id" in entry:
            submissions[str(entry["job_id"])] = str(entry["conversation_id"])
    return submissions
