"""Rewrite the symbols a claim's meaning depends on into words."""

import re

# Each of these three collisions was reproduced on 2026-09-17 against the real
# normalizer: "retention limit -3 days" matched "retention limit 3 days",
# "x >= 3" matched "x < 3", and "version 1.2" matched "version 1-2". Folding
# punctuation away is right for markup and wrong for arithmetic, so the symbols
# that carry meaning become words before the folding runs.
_SUBSTITUTIONS = (
    (re.compile(r">="), " gte "),
    (re.compile(r"<="), " lte "),
    (re.compile(r"!=|≠"), " ne "),
    (re.compile(r">"), " gt "),
    (re.compile(r"<"), " lt "),
    (re.compile(r"="), " eq "),
    (re.compile(r"%"), " pct "),
    # A minus is a sign when it opens a number and a separator between two.
    (re.compile(r"(?<![\w.])-(?=\d)"), " neg "),
    (re.compile(r"(?<=\d)\.(?=\d)"), "dot"),
    (re.compile(r"(?<=\d)-(?=\d)"), "dash"),
    (re.compile(r"(?<=\d)/(?=\d)"), "slash"),
    (re.compile(r"(?<=\d):(?=\d)"), "colon"),
    (re.compile(r"(?<=\d),(?=\d)"), "comma"),
)


def protected_symbols(text: str) -> str:
    """Return the text with meaning-bearing symbols spelled out.

    Applied before accents and markup are folded, so a comparison, a sign and
    a version separator survive into the comparison key instead of being
    flattened into whitespace.
    """
    for pattern, replacement in _SUBSTITUTIONS:
        text = pattern.sub(replacement, text)
    return text
