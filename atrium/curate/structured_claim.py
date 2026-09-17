"""One screened candidate after a model has given it a structure."""

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class StructuredClaim:
    """A claim in fields, still carrying the sentence and provenance it came from.

    ``text`` is kept verbatim beside the structure so a reviewer can check the
    extraction without opening the ledger, and so a later merge can prefer a
    phrasing over a reconstruction.
    """

    candidate_id: str
    text: str
    subject: str
    predicate: str
    value: str
    conditions: str | None
    scope: str
    scope_name: str | None
    project: str | None
    durability: str
    first_seen: str
    last_seen: str
    episodes: int
    model: str

    def as_json(self) -> dict[str, Any]:
        """The ledger line for this claim."""
        return dataclasses.asdict(self)
