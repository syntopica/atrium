"""Where the segment store beside an archive publishes its active generation."""

import json
from pathlib import Path


def active_generation_segments(archive: Path) -> Path | None:
    """Return the active generation's segments directory, or None without one.

    Scribe keeps the v2 store at ``<archive directory>/segments``, names the
    selected generation in ``current-generation.json`` and publishes each new
    segment into ``generations/g_<id>/segments``, so that directory's mtime is
    the time of the newest capture that changed anything.
    """
    reference = archive.parent / "segments" / "current-generation.json"
    try:
        generation = json.loads(reference.read_text()).get("generationId")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(generation, str) or not generation:
        return None
    published = archive.parent / "segments" / "generations" / f"g_{generation}" / "segments"
    return published if published.is_dir() else None
