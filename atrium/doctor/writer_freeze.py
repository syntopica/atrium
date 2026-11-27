"""Whether the conversation writers are frozen, which stops every refresh."""

import time
from pathlib import Path

from atrium.doctor.finding import Finding
from atrium.doctor.refresh_health import BROKEN_AFTER_SECONDS


def writer_freeze(sentinel: Path, now: float | None = None) -> Finding:
    """Report a present freeze sentinel and how long it has been there.

    While the sentinel exists every refresh logs `frozen` and exits 0, so the
    only visible symptom is an index that stops aging well. On 2026-11-24 an
    interrupted `conversation-writers freeze` left one behind and the doctor
    said "archive last written 293902s ago" for three days without naming it.
    A freeze is a migration window, so a young one only warns; one older than a
    refresh is allowed to be dead was forgotten, and fails the run.
    """
    if not sentinel.exists():
        return Finding(
            check="freeze",
            severity="ok",
            code="writers_unfrozen",
            summary="conversation writers are not frozen",
            detail={"sentinel": str(sentinel)},
        )
    moment = time.time() if now is None else now
    age = moment - sentinel.stat().st_mtime
    severity = "broken" if age > BROKEN_AFTER_SECONDS else "warn"
    return Finding(
        check="freeze",
        severity=severity,
        code="writers_frozen_abandoned" if severity == "broken" else "writers_frozen",
        summary=(
            f"conversation writers frozen {int(age)}s ago by {sentinel}; every refresh "
            "is skipped until `conversation-writers unfreeze`"
        ),
        detail={"age_seconds": int(age), "sentinel": str(sentinel)},
    )
