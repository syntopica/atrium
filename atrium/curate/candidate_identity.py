"""The stable id of a claim candidate, derived from its comparison form."""

import hashlib

_LENGTH = 24


def candidate_identity(normalized: str) -> str:
    """Hash the normalized claim, so the same claim keeps its id across runs.

    Identity is content, never position: a ledger rebuilt after the registry
    grows must keep the ids a reviewer has already decided on, or every
    decision is orphaned by the next pass.
    """
    return hashlib.sha256(normalized.encode()).hexdigest()[:_LENGTH]
