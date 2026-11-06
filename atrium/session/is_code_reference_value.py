"""Tell a dotted reference into code from a credential."""

import re


def is_code_reference_value(value: str) -> bool:
    """Whether the value is identifier segments after a lowercase root.

    ``process.env.STRIPE_SECRET_KEY`` or ``metrics.done_1h``. A JWT also has
    dots, but its segments open with ``eyJ``, never a lowercase word.
    """
    segments = value.split(".")
    return (
        len(segments) >= 2  # noqa: PLR2004 -- a root and one member make a reference
        and re.fullmatch(r"[a-z]+", segments[0]) is not None
        and all(re.fullmatch(r"[A-Za-z_$][\w$]*", segment) for segment in segments)
    )
