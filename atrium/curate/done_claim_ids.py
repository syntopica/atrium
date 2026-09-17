"""Which candidates a claims ledger already holds."""

import json
from pathlib import Path


def done_claim_ids(path: Path) -> set[str]:
    """Return the candidate ids already extracted, so a run resumes.

    A truncated last line is ignored rather than fatal: the run before this
    one may have been killed mid-write, and re-extracting one claim is
    cheaper than refusing to start.
    """
    if not path.exists():
        return set()
    done: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                done.add(json.loads(line)["candidate_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done
