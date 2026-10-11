"""One digest for the exact rows a conversation reconciles to."""

import dataclasses
import hashlib
import json
from collections.abc import Iterable

from atrium.record import Record


def rows_sha256(records: Iterable[Record]) -> str:
    """Hash ``records`` order-independently, every field included.

    Sorted the way ``write_conversation`` compares stored rows, so two runs that
    would write the same set produce the same digest whatever order the source
    yielded them in. Every field is in it: a changed title or workspace is a
    changed row, exactly as the stored-row comparison treats it.
    """
    rows = sorted(dataclasses.astuple(record) for record in records)
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
