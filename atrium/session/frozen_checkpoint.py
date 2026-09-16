"""Freeze the boundary a refused Stop will be recorded against."""

import hashlib
from typing import Any

from atrium.session.normalize_timestamp import normalize_timestamp
from atrium.session.transcript_scan import TranscriptScan


def frozen_checkpoint(
    session_id: str, scan: TranscriptScan, since: str | None
) -> dict[str, Any] | None:
    """Return the pending-checkpoint dict for the scan's boundary, or None.

    Frozen before the refusal is printed, so the recording tool call's own
    records fall outside the episode and a retry names the same boundary.
    """
    if scan.boundary is None:
        return None
    digest = hashlib.sha256(f"{session_id}\x00{scan.boundary.uuid}".encode()).hexdigest()
    return {
        "id": digest[:16],
        "boundary_uuid": scan.boundary.uuid,
        "boundary_offset": scan.boundary.offset,
        "boundary_at": normalize_timestamp(scan.boundary.timestamp),
        "since": since,
        "model": scan.model,
        "attempts": 1,
    }
