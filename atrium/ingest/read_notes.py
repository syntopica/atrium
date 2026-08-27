"""Stream curated markdown notes out of a directory tree."""

import hashlib
from collections.abc import Iterator
from pathlib import Path


def read_notes(root: Path, exclude: tuple[str, ...] = ()) -> Iterator[dict]:
    """Yield one dict per markdown file under ``root``, in a deterministic order.

    Reads only ``*.md``, skipping hidden directories and ``node_modules``
    always, plus any directory named in ``exclude``. The exclusion exists
    because a curated tree often carries a raw-material subtree -- brain's
    ``sources/`` holds 10,934 markdown files of converted third-party content
    against ~230 curated notes -- and vectors are budgeted for the curated
    layer only. The content hash pins the revision, exactly as
    ``provenance.contentSha256`` does for conversations: citations resolve to a
    revision, never to an offset that editing would shift.
    """
    skipped = {"node_modules", *exclude}
    for path in sorted(root.rglob("*.md")):
        parts = path.relative_to(root).parts
        if any(part.startswith(".") or part in skipped for part in parts):
            continue
        raw = path.read_bytes()
        yield {
            "path": path.relative_to(root).as_posix(),
            "text": raw.decode("utf-8", errors="replace"),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
