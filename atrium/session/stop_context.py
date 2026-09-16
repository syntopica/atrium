"""Everything the Stop decision reads about one session, resolved once."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atrium.session.transcript_scan import TranscriptScan


@dataclass(frozen=True)
class StopContext:
    """The session, its transcript scan, and its checkpoint state."""

    session_id: str
    transcript: Path
    cwd: str
    state_path: Path
    state: dict[str, Any]
    consumed: dict[str, Any] | None
    scan: TranscriptScan
