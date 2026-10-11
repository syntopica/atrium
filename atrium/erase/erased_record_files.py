"""The registry files, backups included, synthesized from erased conversations."""

import json
from collections.abc import Collection
from pathlib import Path


def erased_record_files(registry: Path, conversation_ids: Collection[str]) -> list[Path]:
    """Return every record file under ``records*`` whose source was erased.

    The backups a rekey or a reset left beside ``records`` (``records.bak-*``,
    ``records.empty-*``) hold the same model output, so an erasure that skipped
    them would leave the text on disk. A file that is not a JSON record is not
    this function's to judge and is left alone.
    """
    found = []
    for directory in sorted(registry.glob("records*")):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(record, dict) and record.get("conversation_id") in conversation_ids:
                found.append(path)
    return found
