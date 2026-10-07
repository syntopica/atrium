"""Whether a synthesis job already produced its record."""

from pathlib import Path

from atrium.synthesize.record_path import record_path


def has_record(registry: Path, job_key: str) -> bool:
    """Whether ``job_key`` already produced a record; existence is the ledger."""
    return record_path(registry, job_key).exists()
