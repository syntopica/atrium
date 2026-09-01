"""Re-key records whose stamp claims a rule their ids do not follow."""

import json
import os
from pathlib import Path
from typing import Any

from atrium.synthesize.backup_synthesis_records import backup_synthesis_records
from atrium.synthesize.qualify_event_id import qualify_event_id
from atrium.synthesize.rekey_synthesis_record import rekey_synthesis_record
from atrium.synthesize.synthesis_registry import record_path


def repair_mis_stamped_records(
    registry: Path, archive: Path, *, apply: bool = False
) -> dict[str, Any]:
    """Find records the stamp calls current whose ids the archive does not hold.

    `event_id_schema` used to be written from the code's own constant, so a
    synthesis pass running against a not-yet-upgraded archive stamped 2 onto
    schema 1 ids. The stamp-based re-key then skipped precisely those records,
    leaving synthesis that cites events no conversation contains -- memory that
    answers and cannot be checked.

    So this pass does not trust the stamp. It asks the archive: if a record's
    ids are absent from its conversation but qualifying them makes every one
    present, the record is mis-stamped and is re-keyed. A record whose ids are
    absent under both rules is left alone and reported -- that is a different
    fault, and guessing at it would destroy the evidence.
    """
    directory = registry / "records"
    by_conversation: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for path in sorted(directory.glob("*.json")):
        record = json.loads(path.read_text())
        by_conversation.setdefault(record["conversation_id"], []).append((path, record))

    repaired = intact = unexplained = 0
    backup: str | None = None
    with archive.open(encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            conversation = json.loads(line)
            entries = by_conversation.get(conversation["id"])
            if entries is None:
                continue
            present = {event.get("id") for event in conversation.get("events") or []}
            for path, record in entries:
                cited = record["event_ids"]
                if all(member in present for member in cited):
                    intact += 1
                    continue
                qualified = [qualify_event_id(record["conversation_id"], m) for m in cited]
                if not all(member in present for member in qualified):
                    unexplained += 1
                    continue
                repaired += 1
                if not apply:
                    continue
                # Same reasoning as the re-key: renaming onto a hashed key is
                # one-way, so the records are copied aside before the first
                # write and not at all when there is nothing to write.
                if backup is None:
                    backup = str(backup_synthesis_records(registry))
                # Re-key from the record as it truly is, so drop the stamp that
                # lied rather than asking the re-key to distrust it.
                rekeyed = rekey_synthesis_record({**record, "event_id_schema": 1})
                destination = record_path(registry, rekeyed["job_key"])
                temporary = destination.with_suffix(f".tmp-{os.getpid()}")
                temporary.write_text(
                    json.dumps(rekeyed, ensure_ascii=False, sort_keys=True, indent=1)
                )
                temporary.chmod(0o600)
                temporary.replace(destination)
                if destination != path:
                    path.unlink()
    return {
        "repaired": repaired,
        "intact": intact,
        "unexplained": unexplained,
        "applied": apply,
        "backup": backup,
    }
