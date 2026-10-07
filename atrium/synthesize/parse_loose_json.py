"""Lenient JSON parsing for model output."""

import json
import re
from typing import Any, cast


def parse_loose_json(text: str) -> dict[str, Any]:
    """Parse Gemini's JSON, tolerating its two observed sloppinesses.

    Raw control characters inside strings (strict=False accepts them) and
    invalid backslash escapes (repaired to literal backslashes). Anything
    still broken raises and the retry loop takes another attempt.
    """
    try:
        return cast("dict[str, Any]", json.loads(text, strict=False))
    except json.JSONDecodeError:
        repaired = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
        return cast("dict[str, Any]", json.loads(repaired, strict=False))
