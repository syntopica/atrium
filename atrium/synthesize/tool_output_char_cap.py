"""The most of one tool call, tool result or harness message a synthesis call reads."""

# Measured 2026-11-06 on the last 100 MB of the archive: tool results are 26% of
# the text synthesis reads (p50 554, p90 4,332, p99 22,834, max 123,047
# characters). Their head says what ran and their tail how it ended; the body
# in between is logs, and stays verbatim in the canonical archive.
TOOL_OUTPUT_CHAR_CAP = 4_000
