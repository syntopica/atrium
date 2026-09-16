"""Assemble one session record from the frozen checkpoint and the synthesis."""

import hashlib
import json
from typing import Any

from atrium.session.redact_sensitive_text import redact_sensitive_text
from atrium.session.session_conversation_id import session_conversation_id
from atrium.session.session_episode_identity import session_episode_identity
from atrium.session.session_job_identity import session_job_identity
from atrium.session.session_model_id import session_model_id
from atrium.session.session_segmentation import SESSION_SEGMENTATION
from atrium.synthesize.job_identity import GENERATOR_VERSION
from atrium.synthesize.synthesis_schema import OUTPUT_SCHEMA_VERSION

SOURCE = "claude-code"


def build_session_record(
    state: dict[str, Any], pending: dict[str, Any], output: dict[str, Any]
) -> dict[str, Any]:
    """Return the record dict; every string of the output is redacted first."""
    redacted = {
        "title": redact_sensitive_text(output["title"]),
        "summary": redact_sensitive_text(output["summary"]),
        "facts": [redact_sensitive_text(item) for item in output["facts"]],
        "open_ends": [redact_sensitive_text(item) for item in output["open_ends"]],
    }
    conversation_id = session_conversation_id(SOURCE, str(state["session_id"]))
    episode_id = session_episode_identity(conversation_id, str(pending["boundary_uuid"]))
    model_id = session_model_id(str(pending.get("model") or ""))
    output_json = json.dumps(redacted, ensure_ascii=False, sort_keys=True)
    return {
        "job_key": session_job_identity(conversation_id, episode_id, model_id),
        "conversation_id": conversation_id,
        "source": SOURCE,
        "revision_sha256": "",
        "episode_id": episode_id,
        "event_ids": [],
        "event_id_schema": 2,
        "segmentation": SESSION_SEGMENTATION,
        "model_requested": model_id,
        "model_resolved": str(pending.get("model") or "unknown"),
        "prompt_sha256": "",
        "output_schema": OUTPUT_SCHEMA_VERSION,
        "generator": GENERATOR_VERSION,
        "map_chunks": 0,
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "authored_at": pending.get("boundary_at"),
        "workspace": state.get("workspace"),
        "session": {
            "since": pending.get("since"),
            "until": pending.get("boundary_at"),
            "boundary_uuid": pending.get("boundary_uuid"),
            "boundary_offset": pending.get("boundary_offset"),
        },
        "output": redacted,
        "output_sha256": hashlib.sha256(output_json.encode()).hexdigest(),
    }
