"""A stable pseudo-random order over candidate ids."""

import hashlib


def sample_rank(candidate_id: str) -> str:
    """Return the sort key that orders a stratum for sampling.

    Hashing the id rather than shuffling with a seeded RNG keeps the sample
    reproducible across Python versions and, more usefully, stable as the
    ledger grows: a candidate already drawn stays drawn when new ones arrive,
    so a second run extends the sample instead of replacing it.
    """
    return hashlib.sha256(f"curate-sample:{candidate_id}".encode()).hexdigest()
