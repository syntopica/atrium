"""Re-key a whole synthesis registry onto the schema 2 event id rule."""

import json
import os
from pathlib import Path
from typing import Any

from atrium.synthesize.backup_synthesis_records import backup_synthesis_records
from atrium.synthesize.event_id_schema import EVENT_ID_SCHEMA
from atrium.synthesize.rekey_synthesis_record import rekey_synthesis_record
from atrium.synthesize.synthesis_registry import record_path


def rekey_synthesis_registry(registry: Path, *, apply: bool = False) -> dict[str, Any]:
    """Rewrite every record whose member event ids predate schema 2.

    Rocket Agents re-keyed archive event ids, and an episode's identity is a
    hash of its member ids. Left alone, every conversation whose archived
    record is upgraded would look like a new episode: `synthesize` would pay
    the model for output this registry already holds, and `ingest-synthesis`
    would index both generations of it. The new ids are a pure function of the
    old ones, so nothing has to be produced again -- only renamed.

    A record moves to a new file because the job key is its name. The old file
    is removed only after the new one exists, so an interrupted pass leaves
    both rather than neither; the re-key is idempotent, so repeating it settles
    that. A record whose new name is already taken by different content is left
    alone and reported: the registry surfaces divergence rather than resolving
    it by arrival order.

    A write pass copies `records/` aside before its first write, and only if it
    has one to make. Renaming is one-way -- a job key is a hash and the old
    identity cannot be recovered from the new one -- and a pass run before the
    archive is upgraded renames every record onto ids the archive does not
    carry yet. The backup is what makes that mistake survivable; a re-run with
    nothing left to do writes neither records nor a second copy of them.
    """
    moved = already = collided = 0
    collisions: list[str] = []
    backup: str | None = None
    for path in sorted((registry / "records").glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("event_id_schema") == EVENT_ID_SCHEMA:
            already += 1
            continue
        rekeyed = rekey_synthesis_record(record)
        destination = record_path(registry, rekeyed["job_key"])
        taken = destination.exists() and destination != path
        if taken and json.loads(destination.read_text()) != rekeyed:
            collided += 1
            collisions.append(rekeyed["job_key"])
            continue
        moved += 1
        if not apply:
            continue
        if backup is None:
            backup = str(backup_synthesis_records(registry))
        temporary = destination.with_suffix(f".tmp-{os.getpid()}")
        temporary.write_text(json.dumps(rekeyed, ensure_ascii=False, sort_keys=True, indent=1))
        temporary.chmod(0o600)
        temporary.replace(destination)
        if destination != path:
            path.unlink()
    return {
        "moved": moved,
        "already": already,
        "collided": collided,
        "collisions": collisions[:10],
        "applied": apply,
        "backup": backup,
    }
