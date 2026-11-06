"""Tell an AEAT liquidation or debt key from a credential."""

import re


def is_tax_reference_value(value: str) -> bool:
    """Whether the value is one uppercase letter and sixteen digits.

    Labelled ``clave``, it reads as a key, and it recurs in every session about
    the tax position.
    """
    return re.fullmatch(r"[A-Z]\d{16}", value) is not None
