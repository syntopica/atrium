"""Explicitly prepare an existing derived store for efficient context reads."""

import json
from pathlib import Path

from atrium.context.context_index_specs import context_index_specs
from atrium.context.context_indexes_ready import context_indexes_ready
from atrium.store.open_store import open_store


def prepare_context_cli(index: Path) -> int:
    """Create additive indexes and report row invariants as JSON."""
    reader = open_store(index, read_only=True)
    try:
        before = reader.execute("SELECT count(*) FROM records").fetchone()[0]
        already_ready = context_indexes_ready(reader)
    finally:
        reader.close()
    writer = open_store(index)
    try:
        after = writer.execute("SELECT count(*) FROM records").fetchone()[0]
        ready = context_indexes_ready(writer)
    finally:
        writer.close()
    print(
        json.dumps(
            {
                "status": "ready" if ready else "unavailable",
                "already_ready": already_ready,
                "indexes": list(context_index_specs()),
                "records_before": before,
                "records_after": after,
            }
        )
    )
    return 0 if ready and before == after else 1
