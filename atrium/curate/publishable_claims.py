"""The claims a merge should see, with the debris of later patterns dropped."""

import json
from pathlib import Path
from typing import Any

from atrium.curate.runtime_debris import runtime_debris


def publishable_claims(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return the claims worth clustering, and what was dropped by reason.

    The screen runs again here rather than the ledger being rebuilt. Every new
    debris pattern changes `candidate_id` for nothing and would invalidate the
    evaluation sample and its holdout a third time; filtering at read time
    keeps the sample stable and still keeps the newest patterns in force.
    """
    kept: list[dict[str, Any]] = []
    dropped: dict[str, int] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            claim = json.loads(line)
            reason = runtime_debris(claim["text"])
            if reason is None:
                kept.append(claim)
                continue
            dropped[reason] = dropped.get(reason, 0) + 1
    return kept, dropped
