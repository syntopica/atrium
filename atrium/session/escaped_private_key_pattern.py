"""An escaped PEM key within one line, END marker optional."""

import re

ESCAPED_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----(?:\\[rn]|[A-Za-z0-9+/=])+"
    r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----)?"
)
