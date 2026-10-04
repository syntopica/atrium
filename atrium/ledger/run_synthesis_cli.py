"""Print one `atrium synthesis` view as JSON."""

import json
import time
from pathlib import Path

from atrium.ledger.synthesis_passes import synthesis_passes
from atrium.ledger.synthesis_recent import synthesis_recent
from atrium.ledger.synthesis_record_detail import synthesis_record_detail
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION


def run_synthesis_cli(
    view: str, registry: Path, *, limit: int, days: int, job_key: str | None = None
) -> int:
    """Print ``recent``, ``passes`` or ``show``; an absent record exits 1."""
    now = time.time()
    if view == "recent":
        document = synthesis_recent(registry, now, limit, days)
    elif view == "passes":
        document = synthesis_passes(registry, now, limit)
    else:
        detail = synthesis_record_detail(registry, job_key or "", now)
        if detail is None:
            print(json.dumps({"schemaVersion": STATUS_SCHEMA_VERSION, "error": "not_found"}))
            return 1
        document = detail
    print(json.dumps(document, ensure_ascii=False, sort_keys=True))
    return 0
