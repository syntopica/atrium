"""One claim, with every episode that stated it."""

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class ClaimCandidate:
    """A distinct claim and its provenance, before any model has judged it.

    ``sources`` holds one entry per episode that stated the claim, so a later
    stage can weigh repetition, follow the citation back to the transcript,
    and compare the dates rather than trusting whichever phrasing was written
    last.
    """

    candidate_id: str
    text: str
    normalized: str
    first_seen: str
    last_seen: str
    sources: tuple[dict[str, str], ...]

    def as_json(self) -> dict[str, Any]:
        """The ledger line, with sources sorted so a rerun is byte-identical."""
        return {
            "candidate_id": self.candidate_id,
            "text": self.text,
            "normalized": self.normalized,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "episodes": len(self.sources),
            "sources": sorted(self.sources, key=lambda source: source["job_key"]),
        }
