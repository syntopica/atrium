"""The state behind a checkpoint id, or the refusal to use it."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from atrium.session.boundary_in_transcript import boundary_in_transcript
from atrium.session.find_pending_checkpoint import find_pending_checkpoint
from atrium.session.is_scratch_path import is_scratch_path
from atrium.session.record_outcome import RecordOutcome
from atrium.session.write_session_state import write_session_state


def resolve_pending_checkpoint(
    checkpoint_id: str, environ: Mapping[str, str]
) -> tuple[Path, dict[str, Any], dict[str, Any]] | RecordOutcome:
    """Return ``(state path, state, pending)`` or a ``RecordOutcome`` refusal.

    The exclusions the hook applies are applied again here: a producer that
    sets ``ATRIUM_NO_SESSION_RECORD`` or a scratch transcript is refused even
    if a checkpoint somehow exists for it.
    """
    if environ.get("ATRIUM_NO_SESSION_RECORD"):
        return RecordOutcome(3, stderr="session recording is disabled in this environment")
    found = find_pending_checkpoint(checkpoint_id, environ)
    if found is None:
        return RecordOutcome(3, stderr=f"no pending checkpoint {checkpoint_id!r}")
    state_path, state = found
    pending = state["pending"]
    transcript = Path(str(state.get("transcript_path") or ""))
    if is_scratch_path(str(transcript), environ.get("TMPDIR")):
        return RecordOutcome(3, stderr="scratch sessions are not recorded")
    if not boundary_in_transcript(transcript, str(pending.get("boundary_uuid"))):
        state["pending"] = None
        write_session_state(state_path, state)
        return RecordOutcome(3, stderr="the checkpoint's boundary is no longer in the transcript")
    return state_path, state, pending
