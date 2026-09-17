"""Append one structured claim to the ledger, flushed."""

import json
from pathlib import Path

from atrium.curate.structured_claim import StructuredClaim


def append_claim(path: Path, claim: StructuredClaim) -> None:
    """Write one claim as a JSONL line and flush it.

    Flushed per claim on purpose: the extraction runs for tens of minutes
    against a local model, and a killed run must leave every claim it already
    paid for on disk for the resume to find.
    """
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(claim.as_json(), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
