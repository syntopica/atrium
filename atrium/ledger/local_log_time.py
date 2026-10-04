"""Read the local wall-clock stamp the pass wrapper writes, as epoch seconds."""

import time


def local_log_time(stamp: str) -> float | None:
    """Parse ``YYYY-MM-DD HH:MM:SS`` in this machine's zone, or ``None``.

    The wrapper logs with `date '+%F %T'`, which carries no zone; the reader
    runs on the machine that wrote it, so the local zone is the right one.
    """
    try:
        return time.mktime(time.strptime(stamp, "%Y-%m-%d %H:%M:%S"))
    except (ValueError, OverflowError):
        return None
