"""Keep one producer call's synthesis on disk, durably."""

import json
import os
import threading
from pathlib import Path
from typing import Any


def keep_partial(path: Path, partial: dict[str, Any]) -> None:
    """Write ``partial`` and make it survive a power loss before anyone acks it.

    Its worker results are acked right after this returns, and an acked result
    is gone from the worker, so the file has to be on disk first: synced before
    the rename and the directory synced after. Replacing is safe where a record
    write is not: a partial caches a deterministic call, so two writers hold the
    same content and either wins. Keys keep their order: a reduce prompt is
    built from the partials' JSON, so a sorted copy would read back as another
    prompt and miss its own kept reduce.
    """
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(f".tmp-{os.getpid()}-{threading.get_ident()}")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(partial, ensure_ascii=False))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    temporary.replace(path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
