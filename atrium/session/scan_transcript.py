"""Read a transcript's metadata at a cost proportional to what changed."""

import re
from pathlib import Path

from atrium.session.transcript_scan import TranscriptScan
from atrium.session.walk_transcript import walk_transcript

_HEAD_BYTES = 65_536
_ENTRYPOINT = re.compile(r'"entrypoint"\s*:\s*"([^"]+)"')
_TIMESTAMP = re.compile(r'"timestamp"\s*:\s*"([^"]+)"')


def scan_transcript(path: Path, from_offset: int = 0) -> TranscriptScan:
    """Return the transcript's size, entrypoint, boundary, model and new prompts.

    The head gives the entrypoint and the first timestamp; the lines from
    ``from_offset`` (the last consumed checkpoint) give the boundary, the last
    assistant model and the count of prompts since. When nothing eligible
    follows the offset the boundary is searched from the start, once: a Stop
    on a session with no new work is the common case, and it reads only the
    delta.
    """
    size = path.stat().st_size
    with path.open("rb") as handle:
        head = handle.read(_HEAD_BYTES).decode("utf-8", "replace")
    entrypoint = _ENTRYPOINT.search(head)
    first_at = _TIMESTAMP.search(head)
    boundary, model, prompts = walk_transcript(path, min(from_offset, size))
    if boundary is None and from_offset > 0:
        boundary, model, _ = walk_transcript(path, 0)
    return TranscriptScan(
        size=size,
        entrypoint=entrypoint.group(1) if entrypoint else None,
        first_at=first_at.group(1) if first_at else None,
        boundary=boundary,
        model=model,
        prompts_after=prompts,
    )
