"""Repeat a refusal for a checkpoint the model has not consumed yet."""

from typing import Any

from atrium.session.refusal_reason import refusal_reason
from atrium.session.stop_context import StopContext
from atrium.session.stop_limits import MAX_ATTEMPTS
from atrium.session.stop_refusal import stop_refusal
from atrium.session.write_session_state import write_session_state


def reissue_refusal(
    context: StopContext, pending: dict[str, Any], *, active: bool
) -> dict[str, object] | None:
    """Refuse again up to the budget, then go quiet; drop it at twice the budget.

    One ignored instruction must not count as completion, so the turn after
    a refusal (``active``) is refused again while attempts remain. Past twice
    the budget the model is not going to write it: the checkpoint is dropped
    rather than taxing every remaining turn, and the batch lanes may take the
    interval.
    """
    attempts = int(pending.get("attempts") or 1)
    if attempts >= 2 * MAX_ATTEMPTS:
        context.state["pending"] = None
        write_session_state(context.state_path, context.state)
        return None
    if active and attempts >= MAX_ATTEMPTS:
        return None
    pending["attempts"] = attempts + 1
    context.state["pending"] = pending
    write_session_state(context.state_path, context.state)
    reason = refusal_reason(str(pending["id"]), pending.get("since"), retry=True)
    return stop_refusal(reason, str(pending["id"]), pending.get("since"), retry=True)
