"""Where one producer call's synthesis is kept on disk."""

import hashlib
import json
from pathlib import Path
from typing import Any


def partial_path(
    partials: Path, model_id: str, system_text: str, user_text: str, tool: dict[str, Any]
) -> Path:
    """Name the result by everything that determines it, never by conversation.

    Two conversations can carry the same text -- seven did on 2026-10-09,
    sharing a 46-character chunk -- and the same model on the same prompt and
    schema is the same synthesis, so they share one file rather than racing for
    one worker key. The tool schema is in the name so a schema change never
    reuses a result shaped for the old one.
    """
    schema = json.dumps(tool, sort_keys=True)
    digest = hashlib.sha256(
        "\0".join((model_id, system_text, user_text, schema)).encode()
    ).hexdigest()
    return partials / f"{digest}.json"
