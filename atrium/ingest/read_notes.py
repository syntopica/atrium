"""Stream curated markdown notes out of a directory tree."""

import hashlib
from collections.abc import Iterator
from pathlib import Path

from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.git_visible_paths import git_visible_paths


def read_notes(
    root: Path, exclude: tuple[str, ...] = (), tally: AdmissionTally | None = None
) -> Iterator[dict[str, str]]:
    """Yield one dict per markdown file under ``root``, in a deterministic order.

    Reads only ``*.md``, skipping hidden directories and ``node_modules``
    always, plus any directory named in ``exclude``. The exclusion exists
    because a curated tree often carries a raw-material subtree -- brain's
    ``sources/`` holds 10,934 markdown files of converted third-party content
    against ~230 curated notes -- and vectors are budgeted for the curated
    layer only. The content hash pins the revision, exactly as
    ``provenance.contentSha256`` does for conversations: citations resolve to a
    revision, never to an offset that editing would shift.

    A file its own repository ignores is not read at all: a notes tree already
    declares what counts as content, and honouring that is what keeps two
    machines indexing the same set. ``exclude`` remains for trees that are not
    repositories, and for raw subtrees a repository does track.
    """
    skipped = {"node_modules", *exclude}
    visible = git_visible_paths(root)
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        offender = next((part for part in parts if part.startswith(".") or part in skipped), None)
        if offender is not None:
            if tally:
                rule = "hidden directory" if offender.startswith(".") else f"excluded {offender}"
                tally.reject(rule)
            continue
        if visible is not None and relative not in visible:
            if tally:
                tally.reject("git-ignored")
            continue
        raw = path.read_bytes()
        yield {
            "path": relative,
            "text": raw.decode("utf-8", errors="replace"),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
