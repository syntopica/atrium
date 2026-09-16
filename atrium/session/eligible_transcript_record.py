"""Parse one transcript line into the fields the scan keeps, or nothing."""

import json
import re
from typing import Any

_ELIGIBLE = re.compile(r'"type"\s*:\s*"(user|assistant)"')


def eligible_transcript_record(line: bytes) -> dict[str, Any] | None:
    """Return the parsed record when it is a user or assistant message.

    Only lines that name one of the two types are parsed at all: a transcript
    is mostly attachments and snapshots, and parsing every line on every Stop
    is what would make the hook slow.
    """
    if not _ELIGIBLE.search(line.decode("utf-8", "replace")[:4096]):
        return None
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict) or record.get("type") not in ("user", "assistant"):
        return None
    if record.get("isMeta") or record.get("isSidechain"):
        return None
    return record
