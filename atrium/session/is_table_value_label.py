"""Recognize a value column next to an explicit credential label."""

import re


def is_table_value_label(cell: str) -> bool:
    """Accept English/Spanish labels with ordinary Markdown decoration."""
    label = re.sub(r"[`*]", "", cell).replace("_", " ").strip().rstrip(":").casefold()
    return label.strip() in {"value", "valor"}
