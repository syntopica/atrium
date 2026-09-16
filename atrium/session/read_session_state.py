"""Read one session's checkpoint state; absent or corrupt reads as empty."""

import json
from pathlib import Path
from typing import Any


def read_session_state(path: Path) -> dict[str, Any]:
    """Return the state dict, or ``{}`` when there is none worth trusting.

    A corrupt file is treated as no state: the registry is the source of
    truth and the worst outcome is one extra reminder, never a lost record.
    """
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}
