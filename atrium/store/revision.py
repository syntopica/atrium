"""What one conversation last reconciled to."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Revision:
    """The stored verdict ``conversation_revisions`` holds for one conversation."""

    rows_sha256: str
    canonical_workspace: str | None
    disposition: str
