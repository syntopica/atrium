"""Copy the registry's records aside before a pass rewrites their names."""

import shutil
from datetime import UTC, datetime
from pathlib import Path


def backup_synthesis_records(registry: Path) -> Path:
    """Copy `records/` to a timestamped sibling and return where it went.

    The re-key is the one operation here that cannot be undone. A job key is a
    hash, so the old identity is not recoverable from the new one, and the
    records hold model output that was paid for once. The re-key is also only
    correct once the archive it mirrors has been upgraded: run it too early and
    every record is renamed onto ids the archive does not yet carry, which is
    precisely the state nobody can reverse.

    Naming follows the registry's existing `.bak-<UTC stamp>` convention, and
    the copy is never merged into an older one -- a second run makes a second
    backup rather than writing into the first, and two runs inside one second
    are separated by a counter rather than colliding.
    """
    records = registry / "records"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    destination = registry / f"records.bak-{stamp}"
    attempt = 1
    while destination.exists():
        attempt += 1
        destination = registry / f"records.bak-{stamp}-{attempt}"
    shutil.copytree(records, destination)
    return destination
