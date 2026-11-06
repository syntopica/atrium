"""Where a conversation marks that every episode of its current content is accounted for."""

import hashlib
from pathlib import Path
from typing import Any

from atrium.synthesize.segment_episodes import SEGMENTATION_FINGERPRINT


def complete_marker(registry: Path, conversation: dict[str, Any]) -> Path | None:
    """Name the marker by conversation, last update and segmentation.

    Deciding that a conversation has nothing left means segmenting it, 1.2 s of
    pure Python each (2026-11-06), so a pass that re-checked every finished
    conversation never got past the newest 7,100 of 65,623 inside its 55-minute
    box. A new event moves ``updatedAt`` and so names a new marker; a stub and
    the conversation it points at carry the same fields, so either can ask.
    shortcut: an edit that changes event ids without moving updatedAt keeps the
    old marker; upgrade to an events hash if a rewrite ever does that.
    """
    stamp = conversation.get("updatedAt") or conversation.get("startedAt")
    if not stamp:
        return None
    key = f"{conversation['id']}\0{stamp}\0{SEGMENTATION_FINGERPRINT}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    return registry / "complete" / digest[:2] / digest
