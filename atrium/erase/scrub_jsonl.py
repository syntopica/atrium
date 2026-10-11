"""Drop the lines of a JSONL file that mention erased identifiers."""

import os
from collections.abc import Collection
from pathlib import Path


def scrub_jsonl(path: Path, needles: Collection[str]) -> int:
    """Rewrite ``path`` without every line containing a needle; return lines dropped.

    Matched as text, not by field: the curation files carry the ids under
    different keys (``candidate_id``, ``left``/``right``, ``members``,
    ``sources``), and a line that names an erased id anywhere was built from it.
    The rewrite is atomic, so a crash leaves the old file or the new one.
    """
    kept = []
    dropped = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if any(needle in line for needle in needles):
                dropped += 1
            else:
                kept.append(line)
    if dropped:
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        temporary.write_text("".join(kept), encoding="utf-8")
        temporary.replace(path)
    return dropped
