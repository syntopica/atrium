"""Stop a pass before it spends the share of the subscription kept for other work."""

from atrium.synthesize.claude_quota_ceiling import CLAUDE_QUOTA_CEILING
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError


def refuse_over_ceiling(utilization: float | None) -> None:
    """Raise ``QuotaExhaustedError`` when the last reported utilization is at the ceiling."""
    if utilization is not None and utilization >= CLAUDE_QUOTA_CEILING:
        raise QuotaExhaustedError(
            f"subscription window {utilization:.0%} used, at or past the "
            f"{CLAUDE_QUOTA_CEILING:.0%} synthesis ceiling; the rest waits for the reset"
        )
