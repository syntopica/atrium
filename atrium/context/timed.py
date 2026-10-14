"""Run one retrieval pass and measure its wall time."""

import time
from collections.abc import Callable
from typing import TypeVar

from atrium.context.elapsed_ms import elapsed_ms

T = TypeVar("T")


def timed(run: Callable[[], T]) -> tuple[T, int]:
    """Return ``run()``'s result and the whole milliseconds it took."""
    started = time.perf_counter()
    return run(), elapsed_ms(started)
