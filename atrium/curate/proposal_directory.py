"""Where one proposal run writes what it wants a human to review."""

from datetime import UTC, datetime
from pathlib import Path

from atrium.curate.curation_directory import curation_directory


def proposal_directory(now: datetime | None = None) -> Path:
    """Create and return ``curation/proposals/<run-id>`` for this run.

    Every run gets its own directory, named for the moment it started: a
    proposal is reviewed against the wiki as it was when the run read it, and
    overwriting the previous run would silently rebase a review in progress.
    """
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    directory = curation_directory() / "proposals" / stamp
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory
