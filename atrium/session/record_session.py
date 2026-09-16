"""Write the record for a frozen checkpoint, or consume it as nothing durable."""

import json
from collections.abc import Mapping
from pathlib import Path

from atrium.session.build_session_record import build_session_record
from atrium.session.consume_checkpoint import consume_checkpoint
from atrium.session.invalid_synthesis_error import InvalidSynthesisError
from atrium.session.record_outcome import RecordOutcome
from atrium.session.record_receipt import record_receipt
from atrium.session.resolve_pending_checkpoint import resolve_pending_checkpoint
from atrium.session.validate_synthesis_payload import validate_synthesis_payload
from atrium.synthesize.synthesis_registry import has_record, write_record


def record_session(
    checkpoint_id: str,
    payload_text: str,
    registry: Path,
    environ: Mapping[str, str],
    *,
    nothing_durable: bool = False,
) -> RecordOutcome:
    """Resolve the checkpoint, validate, redact, write, and mark it consumed."""
    resolved = resolve_pending_checkpoint(checkpoint_id, environ)
    if isinstance(resolved, RecordOutcome):
        return resolved
    state_path, state, pending = resolved
    if nothing_durable:
        consume_checkpoint(state_path, state, pending, None)
        return RecordOutcome(0, stdout="checkpoint consumed: nothing durable recorded")
    try:
        output = validate_synthesis_payload(json.loads(payload_text or ""))
    except ValueError as error:
        reason = str(error) if isinstance(error, InvalidSynthesisError) else "stdin is not JSON"
        return RecordOutcome(2, stderr=f"invalid payload: {reason}")
    record = build_session_record(state, pending, output)
    existed = has_record(registry, record["job_key"])
    write_record(registry, record["job_key"], record)
    consume_checkpoint(state_path, state, pending, record["job_key"])
    return RecordOutcome(0, stdout=json.dumps(record_receipt(record, existed), ensure_ascii=False))
