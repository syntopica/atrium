"""The immutable, content-addressed registry of synthesis records."""

import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path

DEFAULT_REGISTRY = (
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "atrium" / "synthesis"
)


def record_path(registry: Path, job_key: str) -> Path:
    return registry / "records" / f"{job_key}.json"


def has_record(registry: Path, job_key: str) -> bool:
    return record_path(registry, job_key).exists()


def write_record(registry: Path, job_key: str, record: dict) -> Path:
    """Write one record, atomically, never overwriting.

    Records are immutable: the job key hashes every input and recipe field,
    so the same key must always hold the same content. An existing file is
    left untouched rather than rewritten -- if two machines ever disagree
    about a key's content, that is a divergence to surface, not to overwrite
    (never resolved by timestamps).
    """
    path = record_path(registry, job_key)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # The temporary name carries the thread id as well as the pid: a pass runs
    # its conversations in a thread pool, so a pid alone lets two threads share
    # one scratch file and interleave their writes.
    temporary = path.with_suffix(f".tmp-{os.getpid()}-{threading.get_ident()}")
    temporary.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1))
    temporary.chmod(0o600)
    try:
        # os.link fails when the destination exists, so the claim is atomic.
        # os.rename would replace it instead, silently resolving by arrival
        # order the divergence this registry exists to surface.
        os.link(temporary, path)
    except FileExistsError:
        pass
    finally:
        temporary.unlink(missing_ok=True)
    return path


def read_records(registry: Path) -> Iterator[dict]:
    directory = registry / "records"
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.json")):
        yield json.loads(path.read_text())
