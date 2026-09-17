"""Where stage two writes its structured claims."""

from pathlib import Path

CLAIMS = "claims.jsonl"


def claims_ledger_path(directory: Path) -> Path:
    """The claims ledger inside a curation directory."""
    return directory / CLAIMS
