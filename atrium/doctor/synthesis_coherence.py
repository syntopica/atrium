"""Whether the synthesis registry still describes conversations that exist."""

import json
from pathlib import Path

from atrium.doctor.finding import Finding


def synthesis_coherence(registry: Path, archive_ids: set[str]) -> Finding:
    """Count synthesis records whose conversation is no longer in the archive.

    Synthesis is what semantic recall answers from, so a record pointing at a
    conversation the archive no longer holds is memory with nothing behind it:
    it can be cited and cannot be checked. Orphans are reported, never deleted
    here -- the registry holds model output that was paid for once, and an
    archive that shrank is more likely a capture defect than a real removal.
    """
    directory = registry / "records"
    if not directory.is_dir():
        return Finding(
            check="synthesis",
            severity="ok",
            summary="no synthesis registry on this machine",
            detail={"registry": str(registry)},
        )
    total = 0
    orphans: set[str] = set()
    for path in directory.glob("*.json"):
        total += 1
        conversation = json.loads(path.read_text()).get("conversation_id")
        if conversation not in archive_ids:
            orphans.add(conversation)
    return Finding(
        check="synthesis",
        severity="warn" if orphans else "ok",
        summary=f"{total} synthesis records, {len(orphans)} conversations no longer archived",
        detail={"records": total, "orphan_conversations": sorted(orphans)[:20]},
    )
