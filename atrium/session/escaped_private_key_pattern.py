"""An escaped PEM key within one line, END marker optional; its escapes may be doubled.

An encrypted key carries its RFC 1421 headers between the escapes.
"""

import re

ESCAPED_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----(?:(?:Proc-Type|DEK-Info): [A-Za-z0-9,-]+|\\+[rn]|[A-Za-z0-9+/=])+"
    r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----)?"
)
