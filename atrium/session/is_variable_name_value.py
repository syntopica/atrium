"""Tell the name of an environment variable from its value."""

import re


def is_variable_name_value(value: str) -> bool:
    """Whether the value is uppercase words joined by underscores, as ``CONTEXT7_API_KEY``.

    A config saying which variable holds the key does not hold the key.
    """
    return re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+", value) is not None
