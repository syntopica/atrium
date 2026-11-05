"""When the canonical archive was last written, in whichever format."""

from pathlib import Path

from atrium.doctor.active_generation_segments import active_generation_segments


def archive_written_at(archive: Path) -> float | None:
    """Return the newest write to the v1 file or the v2 store, or None for neither.

    Since the 2026-11-05 cutover the v1 file is never written, so its mtime
    alone called a live archive stale. Taking the newer of the two keeps a
    rollback to v1 reading as fresh as well.
    """
    moments = []
    if archive.exists():
        moments.append(archive.stat().st_mtime)
    segments = active_generation_segments(archive)
    if segments is not None:
        moments.append(segments.stat().st_mtime)
    return max(moments) if moments else None
