"""Where a synthesis record lives in the registry."""

from pathlib import Path


def record_path(registry: Path, job_key: str) -> Path:
    """Where ``job_key``'s record lives; the key is the filename."""
    return registry / "records" / f"{job_key}.json"
