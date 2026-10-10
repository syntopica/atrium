"""The document the synthesis job publishes when a pass ends."""

from typing import Any

from atrium.status.iso_utc import iso_utc
from atrium.status.status_schema_version import STATUS_SCHEMA_VERSION
from atrium.status.synthesis_pass import SynthesisPass


def synthesis_status(last: SynthesisPass, now: float) -> dict[str, Any]:
    """Describe the last pass with counts and instants only, never episode content."""
    return {
        "schemaVersion": STATUS_SCHEMA_VERSION,
        "writtenAt": iso_utc(now),
        "lastPass": {
            "producer": last.producer,
            "startedAt": iso_utc(last.started),
            "finishedAt": iso_utc(last.finished),
            "conversations": last.conversations,
            "synthesized": last.synthesized,
            "skipped": last.skipped,
            "failed": last.failed,
            "deferred": last.deferred,
            "trivial": last.trivial,
        },
    }
