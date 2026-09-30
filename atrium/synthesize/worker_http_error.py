"""Translate a coordinator refusal into the exception a synthesis pass acts on."""

import json
import re
from http import HTTPStatus
from urllib.error import HTTPError

from atrium.synthesize.quota_exhausted_error import QuotaExhaustedError

# The coordinator answers errors as {"error": "<allowlisted code>"}; anything
# else in a body is not trusted into a message.
_CODE = re.compile(r"^[a-z0-9_]{1,64}$")


def worker_http_error(error: HTTPError) -> Exception:
    """Return the exception to raise for one non-2xx coordinator answer.

    A 429 is the producer's queue at ``max_outstanding``: nothing submitted
    this pass can be accepted until earlier jobs are collected, so it stops the
    pass like a quota wall rather than failing each conversation in turn. The
    message never says "cooling until": the tick script reads that phrase as
    every task runner resting and switches lanes on it.
    """
    try:
        body = json.loads(error.read() or b"{}")
        code = body.get("error", "") if isinstance(body, dict) else ""
    except (OSError, ValueError):
        code = ""
    code = code if isinstance(code, str) and _CODE.match(code) else "unknown"
    if error.code == HTTPStatus.TOO_MANY_REQUESTS:
        return QuotaExhaustedError(f"worker queue full ({code}); retry on a later pass")
    if error.code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
        return RuntimeError(f"worker refused the request body as too large ({code})")
    return RuntimeError(f"worker answered HTTP {error.code} ({code})")
