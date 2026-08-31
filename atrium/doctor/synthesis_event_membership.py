"""Whether synthesis still cites events its conversation actually holds."""

import json
import random
from pathlib import Path

from atrium.doctor.finding import Finding


def synthesis_event_membership(archive: Path, registry: Path, sample: int = 60, seed: int = 0):
    """Check that a sample of synthesis records cite events that still exist.

    Stronger than asking whether the conversation exists. A synthesis whose
    member events are gone is memory that can be cited and cannot be checked:
    it still answers queries, and nothing behind it supports the answer. This
    is exactly the state an event id rule change produces if the registry is
    not re-keyed, and it is the one check neither store can make alone.

    Sampled and seeded rather than exhaustive: it streams a four-gigabyte file
    once, and one broken membership is already the whole finding.
    """
    directory = registry / "records"
    if not directory.is_dir() or not archive.exists():
        return Finding(
            check="synthesis-events",
            severity="ok",
            summary="no synthesis registry or archive on this machine",
            detail={},
        )
    paths = sorted(directory.glob("*.json"))
    if not paths:
        return Finding(
            check="synthesis-events",
            severity="ok",
            summary="registry holds no records",
            detail={},
        )
    chosen = random.Random(seed).sample(paths, min(sample, len(paths)))
    wanted: dict[str, list[dict]] = {}
    for path in chosen:
        record = json.loads(path.read_text())
        wanted.setdefault(record["conversation_id"], []).append(record)

    missing_records = 0
    missing_events = 0
    checked_events = 0
    absent_conversations = 0
    seen: set[str] = set()
    with archive.open(encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            conversation = json.loads(line)
            records = wanted.get(conversation["id"])
            if records is None:
                continue
            seen.add(conversation["id"])
            present = {event.get("id") for event in conversation.get("events") or []}
            for record in records:
                gone = [member for member in record["event_ids"] if member not in present]
                checked_events += len(record["event_ids"])
                if gone:
                    missing_records += 1
                    missing_events += len(gone)
    absent_conversations = len(set(wanted) - seen)

    broken = missing_records or absent_conversations
    return Finding(
        check="synthesis-events",
        severity="broken" if broken else "ok",
        summary=(
            f"{len(chosen)} sampled records, {checked_events} member events, "
            f"{missing_events} no longer in their conversation, "
            f"{absent_conversations} conversations absent"
        ),
        detail={
            "sampled_records": len(chosen),
            "checked_events": checked_events,
            "records_with_missing_events": missing_records,
            "missing_events": missing_events,
            "absent_conversations": absent_conversations,
        },
    )
