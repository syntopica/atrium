"""Whether the unrecorded transcript has crossed the reminder limits."""

from datetime import datetime

from atrium.session.stop_limits import (
    MAX_UNRECORDED_SECONDS,
    MIN_NEW_BYTES_AGED,
    MIN_NEW_PROMPTS,
)


def over_stop_limits(
    new_bytes: int, prompts_after: int, baseline_at: str | None, now: datetime
) -> bool:
    """True past the prompt limit, or once an interval holding work has aged.

    Size is not a trigger. One turn of tool-heavy work writes hundreds of
    kilobytes of eligible records, so a byte limit fires on every turn while
    saying nothing about whether anything worth an episode happened.
    """
    if prompts_after <= 0:
        return False
    if prompts_after >= MIN_NEW_PROMPTS:
        return True
    if new_bytes < MIN_NEW_BYTES_AGED or not baseline_at:
        return False
    started = datetime.fromisoformat(baseline_at.replace("Z", "+00:00"))
    return (now - started).total_seconds() >= MAX_UNRECORDED_SECONDS
