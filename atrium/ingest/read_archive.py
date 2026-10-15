"""Stream conversations out of a canonical rocket-agents archive."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from atrium.ingest.archive_conversations import archive_conversations


def read_archive(path: Path) -> Iterator[dict[str, Any]]:
    """Yield every conversation object in a canonical export or archive file.

    The file is JSONL whose first line is a manifest (``kind`` =
    ``rocket-agents-conversation-export``) and whose remaining lines are
    conversations. The manifest is skipped rather than validated here; verifying
    its ``contentSha256`` is layer 1's job, and duplicating that check would give
    Atrium a second opinion about a file it does not own.

    Malformed lines raise. A partially readable archive is a layer 1 defect and
    must not be silently half-ingested: the resulting index would look complete.
    """
    with path.open(encoding="utf-8") as handle:
        yield from archive_conversations(handle, path)
