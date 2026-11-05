"""Classify a failed Claude Code CLI call as a quota wall or an ordinary error."""

from atrium.synthesize.claude_cli_quota_markers import CLAUDE_CLI_QUOTA_MARKERS
from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError
from atrium.synthesize.rate_limited_status import RATE_LIMITED_STATUS


def claude_cli_failure(returncode: int, streams: str, api_status: object) -> RuntimeError:
    """Return the error to raise: a spent window must stop the pass, not fail it.

    A quota wall cannot succeed before its reset, so the pass ends at the wall
    instead of writing a FAILED line for every remaining conversation.
    """
    tail = streams.strip()[-400:]
    lowered = streams.lower()
    if api_status == RATE_LIMITED_STATUS or any(m in lowered for m in CLAUDE_CLI_QUOTA_MARKERS):
        return QuotaExhaustedError(tail)
    return RuntimeError(f"claude -p failed ({returncode}): {tail}")
