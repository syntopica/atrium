"""Lone harness notices whose tail varies, so the exact echo set misses them."""

import re

# The whole notice, session id included (1 of 10 Flash records, 2026-10-17); a
# person's message that merely starts the same way does not match.
HARNESS_ECHO_PATTERN = re.compile(
    r"/remote-control is active · Continue here, on your phone, or at "
    r"https://claude\.ai/code/session_\w+"
)
