"""Write the record for a frozen checkpoint, or consume it as nothing durable."""

import json
from collections.abc import Collection, Mapping
from pathlib import Path

from atrium.session.build_session_record import SOURCE, build_session_record
from atrium.session.consume_checkpoint import consume_checkpoint
from atrium.session.invalid_synthesis_error import InvalidSynthesisError
from atrium.session.record_outcome import RecordOutcome
from atrium.session.record_receipt import record_receipt
from atrium.session.resolve_pending_checkpoint import resolve_pending_checkpoint
from atrium.session.session_conversation_id import session_conversation_id
from atrium.session.validate_synthesis_payload import validate_synthesis_payload
from atrium.synthesize.has_record import has_record
from atrium.synthesize.write_record import write_record


def record_session(  # noqa: PLR0913 -- the erased ids come from the instance, which the caller resolves; the session module never chooses one
    checkpoint_id: str,
    payload_text: str,
    registry: Path,
    environ: Mapping[str, str],
    *,
    nothing_durable: bool = False,
    erased: Collection[str] = frozenset(),
) -> RecordOutcome:
    """Resolve the checkpoint, validate, redact, write, and mark it consumed.

    A session whose conversation an erasure removed records nothing: its id is
    the archive's, so writing it would put the erased conversation back. The
    checkpoint is consumed all the same, or the hook would ask again forever.
    """
    resolved = resolve_pending_checkpoint(checkpoint_id, environ)
    if isinstance(resolved, RecordOutcome):
        return resolved
    state_path, state, pending = resolved
    if session_conversation_id(SOURCE, str(state["session_id"])) in erased:
        consume_checkpoint(state_path, state, pending, None)
        return RecordOutcome(0, stdout="checkpoint consumed: this conversation was erased")
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
