"""Count the records the retirement rule keeps out, per retired term."""

from collections import Counter
from pathlib import Path

from atrium.forget.latest_events import latest_events


def forgotten_by_term(ledger: Path) -> dict[str, int]:
    """Return term to the number of records still forgotten under ``retired``."""
    return dict(
        Counter(
            event["detail"]
            for event in latest_events(ledger).values()
            if event["event"] == "forget" and event.get("rule") == "retired"
        )
    )
