"""Normalize a model's nullable answer to None or a non-empty string."""

from typing import Any

_EMPTY = {"", "null", "none", "n/a", "unknown"}


def optional_field(value: Any) -> str | None:
    """Return the trimmed string, or None when the model meant "nothing".

    A grammar forces the type, not the intent: with ``["string", "null"]``
    available, models still write the four-character string "null" as often as
    they write the JSON literal, and an empty field is not a value.
    """
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in _EMPTY else text
