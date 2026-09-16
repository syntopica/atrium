"""A candidate string parsed as a JSON object, or None when it is not one."""

import json
from typing import Any, cast


def parsed_json_object(candidate: str) -> dict[str, Any] | None:
    """Parse leniently (raw control characters allowed) and keep only objects."""
    try:
        parsed = json.loads(candidate, strict=False)
    except json.JSONDecodeError:
        return None
    return cast("dict[str, Any]", parsed) if isinstance(parsed, dict) else None
