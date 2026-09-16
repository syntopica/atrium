"""Whether the unrecorded transcript has crossed the reminder limits."""

from datetime import datetime

from atrium.session.stop_limits import MAX_UNRECORDED_SECONDS, MIN_NEW_BYTES, MIN_NEW_BYTES_AGED


def over_stop_limits(new_bytes: int, baseline_at: str | None, now: datetime) -> bool:
    """True past the byte limit, or past the small limit once the interval aged."""
    if new_bytes >= MIN_NEW_BYTES:
        return True
    if new_bytes < MIN_NEW_BYTES_AGED or not baseline_at:
        return False
    started = datetime.fromisoformat(baseline_at.replace("Z", "+00:00"))
    return (now - started).total_seconds() >= MAX_UNRECORDED_SECONDS
