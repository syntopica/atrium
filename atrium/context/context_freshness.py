"""Read refresh metadata without treating absent metadata as healthy."""

import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atrium.doctor.refresh_health import STALE_AFTER_SECONDS


def context_freshness(state: Path | None) -> dict[str, Any]:
    """Report a stable stamp and freshness classification, never private content."""
    result: dict[str, Any] = {"status": "unknown", "last_refresh": None, "source": None}
    if state is None:
        return result
    stamp = state / "last-refresh"
    result["source"] = str(stamp)
    try:
        value = float(stamp.read_text().strip())
        if not math.isfinite(value) or value < 0 or value > time.time():
            raise ValueError("invalid timestamp")
        result["last_refresh"] = datetime.fromtimestamp(value, UTC).isoformat()
        result["status"] = "stale" if time.time() - value > STALE_AFTER_SECONDS else "fresh"
    except FileNotFoundError:
        pass
    except (OSError, ValueError, OverflowError):
        result["status"] = "invalid"
    return result
