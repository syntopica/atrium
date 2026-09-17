"""Record that a pass over the inputs finished, for the staleness checks."""

import time
from pathlib import Path


def record_refresh(stamp: Path, now: float | None = None) -> None:
    """Write the completion time the doctor, status and context lanes read.

    Nothing in this repository used to write it: the stamp came from a private
    orchestrator, so a freshly installed instance was told forever that no
    refresh had ever completed, with no command it could run to change that.
    An ingest that finished is exactly the event the checks ask about.
    """
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(f"{time.time() if now is None else now}\n", encoding="utf-8")
