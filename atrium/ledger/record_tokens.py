"""The input and output token counts a record says it cost."""

from typing import Any


def record_tokens(record: dict[str, Any]) -> tuple[int, int]:
    """Return ``(input, output)``; a missing or malformed count is zero."""
    usage = record.get("usage")
    if not isinstance(usage, dict):
        return 0, 0
    counts = [usage.get("input_tokens"), usage.get("output_tokens")]
    clean = [
        value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0
        for value in counts
    ]
    return clean[0], clean[1]
