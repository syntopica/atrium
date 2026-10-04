"""Journal one submitted worker job against the conversation it serves."""

import json
from pathlib import Path


def record_worker_submission(journal: Path, job_id: str, conversation_id: str) -> None:
    """Append ``{job_id, conversation_id}``; ids only, never prompt or output text.

    A pass that stops waiting leaves its result to arrive unacknowledged, and
    the worker's results feed names only the job. This journal is how a later
    pass finds the conversation to collect it for. Losing it loses no work:
    the result is still re-found when the walk reaches its conversation.
    """
    journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    line = json.dumps({"job_id": job_id, "conversation_id": conversation_id}) + "\n"
    # One append-mode write per line: concurrent pass threads never interleave.
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(line)
