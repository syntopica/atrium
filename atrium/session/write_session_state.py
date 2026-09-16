"""Write one session's checkpoint state atomically."""

import json
import os
from pathlib import Path
from typing import Any


def write_session_state(path: Path, state: dict[str, Any]) -> None:
    """Replace the state file in one rename, so a reader never sees a torn file."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=1))
    temporary.chmod(0o600)
    temporary.replace(path)
