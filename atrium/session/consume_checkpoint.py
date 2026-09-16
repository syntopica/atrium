"""Mark a session's pending checkpoint consumed, with or without a record."""

from pathlib import Path
from typing import Any

from atrium.session.write_session_state import write_session_state


def consume_checkpoint(
    path: Path, state: dict[str, Any], pending: dict[str, Any], job_key: str | None
) -> None:
    """Move the pending boundary into ``consumed``; the next reminder starts there."""
    state["consumed"] = {
        "offset": pending.get("boundary_offset"),
        "at": pending.get("boundary_at"),
        "job_key": job_key,
    }
    state["pending"] = None
    write_session_state(path, state)
