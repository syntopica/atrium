"""Stream curated markdown notes out of a directory tree."""

import hashlib
from collections.abc import Iterator
from pathlib import Path


def read_notes(root: Path) -> Iterator[dict]:
    """Yield one dict per markdown file under ``root``, in a deterministic order.

    Reads only ``*.md`` and skips hidden directories, so a notes tree that also
    carries binaries and archives (as brain does under ``sources/``) contributes
    only its prose. The content hash pins the revision, exactly as
    ``provenance.contentSha256`` does for conversations: citations resolve to a
    revision, never to an offset that editing would shift.
    """
    for path in sorted(root.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        raw = path.read_bytes()
        yield {
            "path": path.relative_to(root).as_posix(),
            "text": raw.decode("utf-8", errors="replace"),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
