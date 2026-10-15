"""Assemble the registry record of one remembered statement."""

import hashlib
import json
from typing import Any

from atrium.remember.remember_model_id import REMEMBER_MODEL_ID
from atrium.remember.remember_segmentation import REMEMBER_SEGMENTATION
from atrium.remember.remembered_conversation_id import remembered_conversation_id
from atrium.session.redact_sensitive_text import redact_sensitive_text
from atrium.synthesize.job_identity import GENERATOR_VERSION
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION


def build_remembered_record(
    output: dict[str, Any], workspace: str | None, supersedes: list[str], authored_at: str
) -> dict[str, Any]:
    """Return the record dict; every string is redacted, as a session record's is.

    The statement comes from a model's own words, not from the archive, so it
    would otherwise bypass the exporter's redaction. ``supersedes`` names the
    index records this statement replaces; they stay searchable as history.
    """
    redacted = {
        "title": redact_sensitive_text(output["title"]),
        "summary": redact_sensitive_text(output["summary"]),
        "facts": [redact_sensitive_text(item) for item in output["facts"]],
        "open_ends": [redact_sensitive_text(item) for item in output["open_ends"]],
    }
    output_json = json.dumps(redacted, ensure_ascii=False, sort_keys=True)
    targets = sorted(set(supersedes))
    conversation_id = remembered_conversation_id(workspace, output_json, targets)
    return {
        "job_key": conversation_id[:32],
        "conversation_id": conversation_id,
        "source": "remember",
        "revision_sha256": "",
        "episode_id": conversation_id[:24],
        "event_ids": [],
        "event_id_schema": 2,
        "segmentation": REMEMBER_SEGMENTATION,
        "model_requested": REMEMBER_MODEL_ID,
        "model_resolved": REMEMBER_MODEL_ID,
        "prompt_sha256": "",
        "output_schema": OUTPUT_SCHEMA_VERSION,
        "generator": GENERATOR_VERSION,
        "map_chunks": 0,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "authored_at": authored_at,
        "workspace": workspace,
        "supersedes": targets,
        "output": redacted,
        "output_sha256": hashlib.sha256(output_json.encode()).hexdigest(),
    }
