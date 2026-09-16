"""Decide whether a stopping session owes a record, and freeze the boundary."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from atrium.recall.project_workspace import project_workspace
from atrium.session.boundary_in_transcript import boundary_in_transcript
from atrium.session.frozen_checkpoint import frozen_checkpoint
from atrium.session.normalize_timestamp import normalize_timestamp
from atrium.session.over_stop_limits import over_stop_limits
from atrium.session.read_stop_context import read_stop_context
from atrium.session.refusal_reason import refusal_reason
from atrium.session.reissue_refusal import reissue_refusal
from atrium.session.stop_refusal import stop_refusal
from atrium.session.write_session_state import write_session_state


def session_stop_decision(
    payload: dict[str, Any], environ: Mapping[str, str], now: datetime | None = None
) -> dict[str, object] | None:
    """Return the ``{"decision": "block", "reason": ...}`` to print, or None.

    Silent (None) is the common answer: excluded sessions, nothing new, or a
    checkpoint already consumed. A refusal freezes the checkpoint first, so
    the recording turn's own records fall outside the episode.
    """
    context = read_stop_context(payload, environ)
    if context is None:
        return None
    active = bool(payload.get("stop_hook_active"))
    pending = context.state.get("pending")
    if isinstance(pending, dict) and boundary_in_transcript(
        context.transcript, str(pending.get("boundary_uuid"))
    ):
        return reissue_refusal(context, pending, active=active)
    if pending is not None:
        # Its boundary is gone (transcript replaced, `/clear`, another
        # ancestry resumed): that interval is uncovered, and stays so.
        context.state["pending"] = None
        write_session_state(context.state_path, context.state)
    if active or context.scan.prompts_after == 0:
        return None
    consumed = context.consumed
    baseline_at = (
        consumed.get("at") if consumed else normalize_timestamp(context.scan.first_at or "")
    )
    if not over_stop_limits(context.scan.new_bytes, baseline_at, now or datetime.now(UTC)):
        return None
    checkpoint = frozen_checkpoint(context.session_id, context.scan, baseline_at)
    if checkpoint is None:
        return None
    context.state.update(
        session_id=context.session_id,
        transcript_path=str(context.transcript),
        cwd=context.cwd,
        workspace=project_workspace(context.cwd),
        pending=checkpoint,
    )
    write_session_state(context.state_path, context.state)
    reason = refusal_reason(checkpoint["id"], baseline_at, retry=False)
    return stop_refusal(reason, checkpoint["id"], baseline_at)
