"""What one screening pass read, kept and quarantined."""

import dataclasses

from atrium.curate.claim_candidate import ClaimCandidate


@dataclasses.dataclass(frozen=True)
class ScreeningReport:
    """The counts a reviewer needs to trust the screen, not only its output.

    ``reasons`` is per quarantine reason: a screen whose rejections nobody can
    break down is a filter nobody can tune, and the one number that matters --
    how much knowledge it threw away -- would be unmeasurable.
    """

    records: int
    facts: int
    candidates: tuple[ClaimCandidate, ...]
    quarantined: tuple[dict[str, str], ...]
    reasons: dict[str, int]
