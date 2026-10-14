"""Whole milliseconds since a `time.perf_counter()` reading."""

import time


def elapsed_ms(started: float) -> int:
    """Return the wall time since ``started``, rounded to the millisecond."""
    return round((time.perf_counter() - started) * 1000)
