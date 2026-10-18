"""When the client of one service request stops waiting."""

import time
from typing import Any


def request_deadline(request: dict[str, Any]) -> float | None:
    """Return the client's deadline as a ``time.monotonic()`` value, or None.

    The client sends how long it waits (``timeout_s``), not a clock reading,
    so no clock is shared between processes; the request arrives as soon as
    the client connects, so counting from its arrival is close enough. A
    client that sends none (older than this field) gets no deadline.
    """
    timeout = request.get("timeout_s")
    if timeout is None:
        return None
    return time.monotonic() + float(timeout)
