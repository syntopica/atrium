"""Tell a variable that holds a credential from one that describes it."""

import re

from atrium.session.non_secret_variable_words import NON_SECRET_VARIABLE_WORDS

_SECRET_WORD = re.compile(r"(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD)S?$")


def is_secret_variable_name(name: str) -> bool:
    """Segments, not substrings: `TOKENIZER` is not a token, `CF_API_TOKENS` holds some.

    A describing segment (`NON_SECRET_VARIABLE_WORDS`) wins over a credential one.
    """
    segments = name.split("_")
    if any(segment in NON_SECRET_VARIABLE_WORDS for segment in segments):
        return False
    return any(_SECRET_WORD.search(segment) for segment in segments)
