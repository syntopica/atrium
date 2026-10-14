"""Whether a text names any term of a retirement."""

import re

from atrium.context.retirement import Retirement


def names_retirement(text: str, retirement: Retirement) -> bool:
    """Match each term as a whole word, ignoring case."""
    return any(
        re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE)
        for term in retirement.terms
    )
