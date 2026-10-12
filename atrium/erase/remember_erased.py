"""Record erased conversation ids durably, before anything is deleted."""

import os
from collections.abc import Collection
from pathlib import Path

from atrium.erase.erased_conversations_file import erased_conversations_file


def remember_erased(state: Path, conversation_ids: Collection[str]) -> None:
    """Append the ids not yet listed and flush them to disk.

    Kept after the erasure completes, unlike its journal: a live session's
    record carries the archive's conversation id, so a hook that writes after
    the erase would put the conversation back unless something still says it
    was erased.
    """
    path = erased_conversations_file(state)
    created = not path.is_file()
    known = set(path.read_text(encoding="utf-8").split()) if path.is_file() else set()
    missing = sorted(set(conversation_ids) - known)
    if not missing:
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write("".join(f"{conversation_id}\n" for conversation_id in missing))
        handle.flush()
        os.fsync(handle.fileno())
    if created:
        # A new file's name lives in the directory, flushed separately.
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
