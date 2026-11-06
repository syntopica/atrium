"""Tell a code expression or placeholder from a literal credential."""

import re


def is_code_expression_value(value: str) -> bool:
    """Whether an assigned value holds a parenthesis or a bracket.

    ``SECRET=crypto.randomBytes(32).toString('hex')`` names how a secret is made,
    ``KEY = process.argv[3]`` where it comes from, and ``KEY = "[HOME]/.ssh/..."``
    an already-redacted path. A literal credential holds neither.
    """
    return re.search(r"[()[\]]", value) is not None
