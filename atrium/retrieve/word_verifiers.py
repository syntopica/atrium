"""Adjacency checks for punctuated query terms."""

import re

from atrium.retrieve.fold import fold


def word_verifiers(query: str) -> tuple[list[re.Pattern[str]], bool]:
    """Build adjacency checks for punctuated terms, and note plain ones.

    An FTS5 phrase preserves token order but not the punctuation between tokens,
    so the phrase for `3.7.0` also matches `allocate 3 7 0 workers`. Each
    multi-part term therefore gets a regex requiring its parts to be joined by
    punctuation, not whitespace, in the stored text. The filter applies only when
    every term is punctuated: terms are OR-ed, and a hit that fails the regexes
    may still have matched a plain word this function cannot see.

    Patterns are built over diacritic-folded text and must be matched against
    ``fold``-ed text: the index tokenizer removes diacritics, so `café-au-lait`
    finds a stored `cafe-au-lait`, and a verifier comparing raw strings would
    silently throw that legitimate hit away (reproduced by review).
    """
    verifiers = []
    has_plain_term = False
    for raw_term in query.split():
        parts = re.findall(r"[^\W_]+", raw_term, flags=re.UNICODE)
        if not parts:
            continue
        if len(parts) > 1:
            # The separator class is "punctuation": anything that is neither
            # whitespace nor alphanumeric. `_` must be included explicitly --
            # it counts as \w, yet it is exactly what joins snake_case parts.
            joined = r"(?:[^\w\s]|_)+".join(re.escape(fold(part)) for part in parts)
            verifiers.append(re.compile(rf"(?<!\w){joined}(?!\w)", re.IGNORECASE))
        else:
            has_plain_term = True
    return verifiers, has_plain_term
